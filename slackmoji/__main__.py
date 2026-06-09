from slackmoji import Config, load_cookies, EmojiFile, get_url
from typing import Optional
import os
import json
import requests
import click


@click.command()
@click.argument("filename", type=click.Path(exists=True), default=None)
@click.option(
    "--ignore-cache", is_flag=True, help="Ignore cached results and fetch fresh data"
)
@click.option(
    "--just-metadata", is_flag=True, help="Only fetch metadata, skip downloading emoji"
)
@click.option(
    "--verbose", "-v", is_flag=True, help="Enable verbose output for debugging"
)
@click.option("--instance", "-i", type=str, help="Specify the Slack instance to target")
def main(
    filename: Optional[str],
    ignore_cache: bool,
    just_metadata: bool,
    verbose: bool,
    instance: Optional[str],
) -> None:
    config = Config.model_validate({"instance": instance})
    assert config.base_url is not None, (
        "Base URL must be set in environment variable SLACK_BASE_URL"
    )

    cookies = load_cookies()
    assert cookies, "No cookies found in cookies.tsv"

    session = requests.Session()
    session.cookies.update(cookies)

    if not os.path.exists("./output/"):
        os.makedirs("./output/")

    if filename is not None:
        with open(filename, "r") as f:
            data = json.load(f)
            emoji_file = EmojiFile.model_validate(data)
            if verbose:
                print(
                    f"Found {len(emoji_file.emoji)}/{emoji_file.paging.total} emoji in {filename}"
                )
    else:
        emoji_file = get_url(ignore_cache, config, session, page=1, count=1000)

    page = emoji_file.paging.page
    while page <= emoji_file.paging.pages:
        try:
            emoji_file = get_url(
                ignore_cache, config, session, page, emoji_file.paging.count
            )
        except Exception as error:
            print(f"Error fetching page {page}: {error}")
            break
        print(
            "Found {} emoji and {} disabled emoji on page {}".format(
                len(emoji_file.emoji), len(emoji_file.disabled_emoji), page
            )
        )
        if not just_metadata:
            for emoji in emoji_file.emoji:
                emoji.grab(config, verbose)
            for emoji in emoji_file.disabled_emoji:
                emoji.grab(config, verbose)
        page = emoji_file.paging.page + 1


if __name__ == "__main__":
    main()
