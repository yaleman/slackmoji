# slackmoji

Does what it says in the code

* go here `https://<yourinstance>.slack.com/customize/emoji`
* set the `SLACK_BASE_URL` env var to `https://<yourinstance>.slack.com`
* there'll be a POST to `/api/emoji.adminList`
  * grab the token from the request payload and set it to the `SLACK_TOKEN` env var.
  * save the JSON response to a file like `example.json`
* grab the cookies, copy-paste them from chrome into `cookies.tsv`

run the thing, it'll dump all the emoji into `output/emoji/<name>.<extension>` and cache the API responses in `output/`
