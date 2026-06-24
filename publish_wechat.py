#!/usr/bin/env python3
"""
将大盘复盘报告发布到微信公众号草稿箱
用法: python scripts/publish_wechat.py <报告文件路径>
需要环境变量: WECHAT_APPID, WECHAT_APPSECRET
"""
import os, sys, json, re
import requests

def get_access_token(appid: str, secret: str) -> str:
    resp = requests.get(
        "https://api.weixin.qq.com/cgi-bin/token",
        params={"grant_type": "client_credential", "appid": appid, "secret": secret},
        timeout=30
    )
    data = resp.json()
    if "access_token" not in data:
        raise RuntimeError(f"获取access_token失败: {data}")
    return data["access_token"]

def md_to_wechat_html(md_text: str) -> tuple:
    lines = md_text.split("\n")
    title = ""
    body_lines = []
    for line in lines:
        if line.startswith("# ") and not title:
            title = line[2:].strip()
        else:
            body_lines.append(line)
    
    html_parts = []
    in_table = False
    in_code = False
    
    for line in body_lines:
        if line.strip().startswith("```"):
            in_code = not in_code
            if in_code:
                html_parts.append('<pre style="background:#1e1e1e;color:#d4d4d4;padding:12px;border-radius:6px;overflow-x:auto;font-size:13px;line-height:1.6"><code>')
            else:
                html_parts.append('</code></pre>')
            continue
        
        if in_code:
            html_parts.append(line + "\n")
            continue
        
        if "|" in line and line.strip().startswith("|"):
            if not in_table:
                html_parts.append('<table style="width:100%;border-collapse:collapse;margin:10px 0;font-size:13px">')
                in_table = True
            cells = [c.strip() for c in line.split("|")[1:-1]]
            if all(c.replace("-", "").replace(":", "").strip() == "" for c in cells):
                continue
            html_parts.append("<tr>")
            for cell in cells:
                style = "border:1px solid #ddd;padding:6px 8px;text-align:left"
                html_parts.append(f'<td style="{style}">{cell}</td>')
            html_parts.append("</tr>")
            continue
        else:
            if in_table:
                html_parts.append("</table>")
                in_table = False
        
        if line.startswith("### "):
            html_parts.append(f'<h3 style="font-size:16px;color:#2c3e50;margin:20px 0 10px;padding-left:8px;border-left:4px solid #38bdf8">{line[4:]}</h3>')
        elif line.startswith("## "):
            html_parts.append(f'<h2 style="font-size:18px;color:#1a1a2e;margin:24px 0 12px;padding-bottom:6px;border-bottom:2px solid #38bdf8">{line[3:]}</h2>')
        elif line.startswith("> "):
            html_parts.append(f'<blockquote style="background:#f0f7ff;border-left:4px solid #38bdf8;padding:10px 14px;margin:10px 0;color:#555;font-size:14px">{line[2:]}</blockquote>')
        elif line.strip() == "---":
            html_parts.append('<hr style="border:none;border-top:1px dashed #ddd;margin:16px 0">')
        elif line.startswith("- "):
            html_parts.append(f'<li style="margin:4px 0;color:#333;font-size:14px;line-height:1.8">{line[2:]}</li>')
        elif "**" in line:
            text = re.sub(r'\*\*(.+?)\*\*', r'<strong style="color:#e74c3c">\1</strong>', line)
            html_parts.append(f'<p style="margin:6px 0;font-size:14px;color:#333;line-height:1.8">{text}</p>')
        elif line.strip():
            text = line
            if text[0] in "📊📈🎯⚪🟢🔴🟡":
                html_parts.append(f'<p style="margin:8px 0;font-size:15px;font-weight:bold;color:#1a1a2e">{text}</p>')
            else:
                html_parts.append(f'<p style="margin:6px 0;font-size:14px;color:#333;line-height:1.8">{text}</p>')
    
    if in_table:
        html_parts.append("</table>")
    
    body_html = "\n".join(html_parts)
    footer = '<hr style="border:none;border-top:1px solid #eee;margin:20px 0"><p style="text-align:center;color:#999;font-size:12px">🤖 由 AI 自动生成 · 仅供参考，不构成投资建议<br>数据来源：公开市场数据 | 分析模型：DeepSeek</p>'
    
    return title, f'<section style="padding:10px;font-family:-apple-system,BlinkMacSystemFont,sans-serif;max-width:100%;word-break:break-all">{body_html}{footer}</section>'

def publish_draft(access_token: str, title: str, content: str) -> str:
    digest = content[:120].replace("<", "").replace(">", "") + "..."
    payload = {
        "articles": [{
            "title": title,
            "author": "AI股票分析",
            "digest": digest,
            "content": content,
            "content_source_url": "",
            "need_open_comment": 0,
            "only_fans_can_comment": 0,
        }]
    }
    resp = requests.post(
        f"https://api.weixin.qq.com/cgi-bin/draft/add?access_token={access_token}",
        json=payload, timeout=30
    )
    data = resp.json()
    if "media_id" in data:
        return data["media_id"]
    raise RuntimeError(f"发布草稿失败: {data}")

def main():
    if len(sys.argv) < 2:
        reports_dir = os.path.join(os.path.dirname(__file__), "..", "reports")
        files = sorted([f for f in os.listdir(reports_dir) if f.endswith(".md")], reverse=True) if os.path.isdir(reports_dir) else []
        if not files:
            print("❌ 未找到报告文件")
            sys.exit(1)
        report_file = os.path.join(reports_dir, files[0])
    else:
        report_file = sys.argv[1]
    
    appid = os.environ.get("WECHAT_APPID")
    secret = os.environ.get("WECHAT_APPSECRET")
    if not appid or not secret:
        print("⚠️ 跳过: 未配置 WECHAT_APPID / WECHAT_APPSECRET")
        sys.exit(0)
    
    print(f"📄 {report_file}")
    with open(report_file, "r", encoding="utf-8") as f:
        md_text = f.read()
    
    title, html = md_to_wechat_html(md_text)
    print(f"📝 标题: {title}")
    
    token = get_access_token(appid, secret)
    media_id = publish_draft(token, title, html)
    print(f"✅ 草稿已发布 media_id={media_id}")

if __name__ == "__main__":
    main()
