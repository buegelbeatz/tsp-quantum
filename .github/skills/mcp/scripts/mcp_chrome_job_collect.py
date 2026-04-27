"""Collection helpers for homepage discovery and content extraction."""

from __future__ import annotations

from urllib.parse import parse_qs, quote_plus, urlparse

HOME_PAGE_SCRIPT = "async()=>{const i=new Set(['google.com','www.google.com','support.google.com','policies.google.com','accounts.google.com','maps.google.com']);const s=new Set();const h=[];const t=(href)=>{if(!href)return null;if(href.startsWith('http://')||href.startsWith('https://'))return href;if(href.startsWith('/url?')){try{const r=new URL(href,location.origin);const q=r.searchParams.get('q');if(q&&(q.startsWith('http://')||q.startsWith('https://')))return q;}catch(_){return null;}}return null;};for(const a of Array.from(document.querySelectorAll('a[href]'))){const href=a.getAttribute('href')||'';const u=t(href);if(!u)continue;try{const p=new URL(u);const host=p.hostname.toLowerCase();if(i.has(host))continue;const home=`${p.protocol}//${host}/`;if(!s.has(home)){s.add(home);h.push(home);}}catch(_){}}return {homepages:h};}"
DDG_HOME_PAGE_SCRIPT = "async()=>{const i=new Set(['duckduckgo.com','www.duckduckgo.com']);const s=new Set();const h=[];for(const a of Array.from(document.querySelectorAll('a[href]'))){const href=a.getAttribute('href')||'';if(!href.startsWith('http'))continue;try{const p=new URL(href);const host=p.hostname.toLowerCase();if(i.has(host))continue;const home=`${p.protocol}//${host}/`;if(!s.has(home)){s.add(home);h.push(home);}}catch(_){}}return {homepages:h};}"
FINDINGS_SCRIPT = "async()=>{return {title:document.title||'',text:(document.body?.innerText||'').slice(0,5000)}}"


async def collect_homepages_impl(
    session,
    source_url: str,
    limit: int,
    wait_timeout_seconds: int,
    poll_seconds: int,
    *,
    call_text_fn,
    parse_tool_json_fn,
    normalize_host_fn,
    sleep_fn,
    print_fn,
) -> list[str]:
    """Navigate to source URL and collect unique homepage URLs."""
    await session.call_tool(
        "navigate_page", {"type": "url", "url": source_url, "timeout": 30000}
    )
    await sleep_fn(2)

    attempts = max(1, wait_timeout_seconds // max(1, poll_seconds))
    for attempt in range(1, attempts + 1):
        text = await call_text_fn(
            session, "evaluate_script", {"function": HOME_PAGE_SCRIPT}
        )
        payload = parse_tool_json_fn(text)
        homepages = list(payload.get("homepages", []))[: max(limit, 1)]
        if homepages:
            return homepages
        if attempt < attempts:
            print_fn(
                f"Waiting for manual verification/captcha completion... retry {attempt}/{attempts}"
            )
            await sleep_fn(max(1, poll_seconds))

    query = parse_qs(urlparse(source_url).query).get("q", [""])[0].strip()
    if normalize_host_fn(source_url).endswith("google.com") and query:
        ddg_url = f"https://duckduckgo.com/?q={quote_plus(query)}"
        await session.call_tool(
            "navigate_page", {"type": "url", "url": ddg_url, "timeout": 30000}
        )
        await sleep_fn(2)
        text = await call_text_fn(
            session, "evaluate_script", {"function": DDG_HOME_PAGE_SCRIPT}
        )
        payload = parse_tool_json_fn(text)
        return list(payload.get("homepages", []))[: max(limit, 1)]
    return []


async def collect_findings_impl(
    session,
    homepages: list[str],
    *,
    call_text_fn,
    parse_tool_json_fn,
    normalize_host_fn,
    summarize_text_fn,
    sleep_fn,
) -> list[dict[str, str]]:
    """Open each homepage and collect title and compact text excerpt."""
    findings: list[dict[str, str]] = []
    for homepage in homepages:
        await session.call_tool(
            "navigate_page", {"type": "url", "url": homepage, "timeout": 30000}
        )
        await sleep_fn(1.5)
        text = await call_text_fn(
            session, "evaluate_script", {"function": FINDINGS_SCRIPT}
        )
        payload = parse_tool_json_fn(text)
        findings.append(
            {
                "host": normalize_host_fn(homepage),
                "url": homepage,
                "title": payload.get("title", ""),
                "summary": summarize_text_fn(payload.get("text", "")),
            }
        )
    return findings
