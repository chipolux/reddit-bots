A repo consolidating a bunch of my old reddit bots that did various things
like post youtube videos, manage comment sections, update sidebars with stream
info, etc.

These are some super crude and messy scripts and half-baked solutions, most of
them worked alright but eventually were retired over the course of about 4-5
years.

* `approval-bot`
    * A bot that would auto-approve posts marked as spam by reddit. Was used on
      the /r/sips subreddit and a few others at a time when the reddit spam filter
      was overzealous in flagging non-spam posts and the moderators were overwhelmed
      with requests to approve posts.
* `post-bot`
    * A bot that would create a new thread in a configured subreddit each day
      and post a toplevel comment for any youtube videos uploaded that day by
      a list of configured youtube channels. Also would clear out any toplevel
      comments (and their children) that were not made by the bot or a moderator.
      It was used for a while on the /r/Yogscast subreddit to manage the flood
      of video posts from all the yogscast family of youtube channels.
* `sips_bot`
    * A collection of some of the first iterations of my family of reddit bots
      that are event cruder than the others in this repo.
* `steam-bot`
    * A bot that would scour steam every few hours to find any games that were
      on sale (mostly useful during a big steam sale), and aggregate information
      about them and post that summary to a configured subreddit. Intended to
      replace the inaccurate and incomplete sale summaries usually posted on
      places like /r/steamdeals and did take over that roll for a few weeks.
* `twitch-bot`
    * A bot that would watch for configured twitch streams to go live and then
      update a subreddits sidebar to show that status.
* `twitter-bot`
    * A bot that would summarize all the tweets by a configured user each day
      and post that summary with images, links, etc.
* `yogscast-site-bot`
    * A bot that would watch the yogscast's website for new videos, extract
      metadata about them, and then post links to those videos on the /r/Yogscast
      subreddit. Was used when the yogscast started posting their new videos to
      their website a day or so earlier than youtube and then retired when they
      stopped.
* `youtube-bot`
    * The most widely used bot. Was at one point used on /r/Yogscast and just
      about every other yogscast members personal subreddit like /r/sips, /r/sjin,
      /r/YogscastHannah, etc. Does what it says on the tin, it tracks a youtube
      channel and posts any new videos to the configured subreddit. Was intended
      to ensure that the first link to a new video was named nicely and easily
      identifiable as being a real link based on the user and their tags.
