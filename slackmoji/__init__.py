from pathlib import Path
import time
import os
import json

import requests
from typing import List, Dict, Generator, Optional
from pydantic import BaseModel, Field, ConfigDict, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    base_url: str
    token: str
    instance: Optional[str] = Field(
        None, description="Optional Slack instance name for logging purposes"
    )

    model_config = SettingsConfigDict(env_prefix="SLACK_")

    @model_validator(mode="before")
    @classmethod
    def base_url_off_instance(
        cls, values: Dict[str, Optional[str]]
    ) -> Dict[str, Optional[str]]:
        if values.get("instance") and not values.get("base_url"):
            values["base_url"] = f"https://{values['instance']}.slack.com"
        return values


class Emoji(BaseModel):
    name: str
    url: str
    is_alias: bool
    alias_for: str
    synonyms: List[str] = Field(default_factory=list)
    avatar_hash: str
    can_delete: bool
    user_display_name: str

    created: int
    is_bad: bool

    user_id: str
    team_id: str

    model_config = ConfigDict(extra="forbid")

    def filename(self, config: Config) -> Path:
        extension = self.url.split(".")[-1]
        if config.instance:
            return Path("output") / config.instance / f"emoji/{self.name}.{extension}"
        else:
            return Path("output") / f"emoji/{self.name}.{extension}"

    def all_filenames(self, config: Config) -> Generator[Path, None, None]:
        extension = self.url.split(".")[-1]
        yield self.filename(config)
        for synonym in self.synonyms:
            if config.instance:
                yield Path("output") / config.instance / f"emoji/{synonym}.{extension}"
            else:
                yield Path("output") / f"emoji/{synonym}.{extension}"

    def already_grabbed(self, config: Config, debug: bool = False) -> bool:
        for filename in self.all_filenames(config):
            if filename.exists():
                if debug:
                    print(f"Emoji '{self.name}' already exists as {filename}.")
                return True
        return False

    def grab(self, config: Config, verbose: bool, attempts: int = 0) -> None:
        if self.is_alias:
            if verbose:
                print(f"Skipping alias emoji: {self.name} -> {self.alias_for}")
            return
        if self.already_grabbed(config, debug=verbose):
            return
        if attempts > 5:
            print(
                f"Failed to download emoji '{self.name}' after multiple attempts. Skipping."
            )
            return
        try:
            response = requests.get(self.url, stream=True)
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", "60"))
                print(
                    f"Rate limited while downloading '{self.name}'. Retrying after {retry_after} seconds..."
                )
                time.sleep(retry_after + 5)
                return self.grab(config, verbose, attempts + 1)
            response.raise_for_status()
            if not self.filename(config).parent.exists():
                self.filename(config).parent.mkdir(parents=True, exist_ok=True)
            with open(self.filename(config), "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            if verbose:
                print(f"Saved emoji '{self.name}' to {self.filename(config)}")

        except Exception as e:
            print(f"Error downloading emoji '{self.name}': {e}")


class Paging(BaseModel):
    count: int
    total: int
    page: int
    pages: int

    model_config = ConfigDict(extra="forbid")


class EmojiFile(BaseModel):
    ok: bool
    emoji: List[Emoji]
    disabled_emoji: List[Emoji] = Field(default_factory=list)
    custom_emoji_total_count: int
    paging: Paging

    model_config = ConfigDict(extra="forbid")

    def savepath(self, config: Config) -> Path:
        if config.instance:
            return (
                Path("output") / config.instance / f"emoji_page_{self.paging.page}.json"
            )
        else:
            return Path("output") / f"emoji_page_{self.paging.page}.json"


def load_cookies() -> Dict[str, str]:
    if not os.path.exists("cookies.tsv"):
        raise FileNotFoundError(
            "cookies.tsv file not found. Please create it with your Slack cookies."
        )
    with open("cookies.tsv", "r", encoding="utf-8") as fh:
        contents = fh.readlines()
    cookies = {}

    for line in contents:
        if line.startswith("#") or not line.strip():
            continue
        parts = line.strip().split("\t")

        name = parts[0]
        value = parts[1]
        cookies[name] = value
    return cookies


def load_cache(config: Config, page: int) -> Optional[EmojiFile]:
    filepath = Path("./output/")
    if config.instance:
        filepath = filepath / config.instance
    filepath = filepath / f"emoji_page_{page}.json"
    if filepath.exists():
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            emoji_file = EmojiFile.model_validate(data)
        return emoji_file
    else:
        return None


def get_url(
    ignore_cache: bool,
    config: Config,
    session: requests.Session,
    page: int,
    count: int,
    attempt=0,
) -> EmojiFile:
    if not ignore_cache:
        cached_emoji = load_cache(config, page)
        if cached_emoji:
            return cached_emoji
    if attempt > 10:
        raise Exception(f"Maximum retry attempts reached at page {page}")
    url = f"{config.base_url}/api/emoji.adminList"
    payload = {
        "token": config.token,
        "page": page,
        "count": count,
    }
    response = session.post(url, data=payload)
    if response.status_code == 429:
        retry_after = int(response.headers.get("Retry-After", "60"))
        print(f"Rate limited. Retrying after {retry_after} seconds...")
        time.sleep(retry_after + 5)
        return get_url(ignore_cache, config, session, page, count, attempt=attempt + 1)
    response.raise_for_status()
    data = response.json()
    emoji_file = EmojiFile.model_validate(data)
    save_path = emoji_file.savepath(config)
    if not save_path.parent.exists():
        save_path.parent.mkdir(parents=True, exist_ok=True)
    with open(save_path, "w") as f:
        f.write(emoji_file.model_dump_json(indent=2))
    return emoji_file
