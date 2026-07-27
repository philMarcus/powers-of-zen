---
name: zen-post
description: Post the next queued Powers of Zen video to TikTok, YouTube Shorts, and Instagram via the CDP-driven PowersOfZen Chrome profile. Use when asked to post, publish, or run the posting queue. Reads outbox/queue.json for file + captions.
---

# Posting a Powers of Zen video (browser driver playbook)

Inputs come from `outbox/queue.json`: next unposted entry has `file` (repo-relative),
`caption`, `yt_title`, `yt_desc`. Update its `status` after posting. Windows path for
file inject: `C:\Users\Phil\zoomer\<file with backslashes>`.

## Setup
- Chrome must be running with the PowersOfZen profile: `scripts/start_chrome_zen.sh`
  (CDP on :9222). Driver: `python3 scripts/zen_browser.py <cmd> --tab=<url-substring> …`
- Target tabs by URL substring, NEVER by index (tab order changes on activation).
- Screenshots land hi-DPI; **coordinate clicks = displayed-coords × 1.28**
  (viewport 2560 wide, DPR 1.5). Prefer DOM/JS clicks; use coordinates only when
  DOM clicks fail. Toggles usually need a real click + a confirm modal.
- Screenshot → Read → verify after every state change. Never fire a final
  Post/Publish button without a screenshot confirming all fields.

## TikTok (studio)
1. goto `https://www.tiktok.com/tiktokstudio/upload`
2. `setfile 'input[type="file"]' <winpath>` (iframe-piercing built into driver)
3. Accept "automatic content checks" modal (Turn on).
4. Caption: focus `.public-DraftEditor-content` via JS, `document.execCommand('selectAll')`,
   then `type` command with caption text. Blur to dismiss hashtag dropdown.
5. Show more → AI-generated content toggle → confirm "Turn on" in modal.
6. Verify checks passed (music + content: "No issues found"), When=Now,
   visibility=Everyone, then click Post. First posts sit in "Content under
   review" (shown Only-me) until review clears — normal, do not repost.

## YouTube (studio)
1. goto `https://www.youtube.com/upload` on the studio tab; `setfile` same way.
2. Title = `#textbox`[0] (focus, selectAll, type yt_title — MAX 100 chars).
   Description = `ytcp-video-description #textbox` (only exists after render;
   verify non-null or everything lands in the title).
3. Audience: click `tp-yt-paper-radio-button` containing "not made for kids".
4. Show more → AI use → select "Yes" radio (adds disclosure label).
5. `#next-button` ×3 → Visibility: click "Public" radio → `#done-button`.
6. Confirm "Video published" dialog; capture the shorts URL for the queue.

## Instagram
1. goto instagram.com → click "Create" in left nav → "Create new post" dialog.
2. File input is created on demand — use driver `choosefile` command
   (intercepts the native chooser):
   `choosefile "[...document.querySelectorAll('button')].find(b=>/select from computer/i.test(b.textContent)).click()" <winpath>`
3. Crop screen: set aspect to Original (9:16) → Next → Next.
4. Caption into the contenteditable; Advanced settings has an AI label toggle
   when available. → Share. Reel appears on powers.of.zen.

## Cost doctrine (Phil, 2026-07-26)
Premium-model click-driving is expensive. Keep vision checks to the minimum
verification points above; long-term this playbook is executed by a LOCAL
vision-model agent (Ollama VLM harness) with this file as its script — see
PLAN.md "local posting agent". Big-model involvement should shrink to
writing captions and handling novel dialogs.
