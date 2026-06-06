import json, os, sys, re, requests
from datetime import datetime, timezone
import google.auth.transport.requests
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import anthropic

VIDEOS_JSON = "videos.json"

def get_youtube_service():
    creds = Credentials(
        token=None,
        refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["YOUTUBE_CLIENT_ID"],
        client_secret=os.environ["YOUTUBE_CLIENT_SECRET"],
        scopes=["https://www.googleapis.com/auth/youtube.upload"],
    )
    creds.refresh(google.auth.transport.requests.Request())
    return build("youtube", "v3", credentials=creds)

def download_video(sora_link, output_path="video.mp4"):
    print(f"[↓] Downloading from soravideo: {sora_link}")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        resp = requests.post("https://soravideo.com/api/download", json={"url": sora_link}, headers=headers, timeout=30)
        data = resp.json()
        download_url = data.get("downloadUrl") or data.get("url") or data.get("mp4")
        if not download_url:
            raise Exception("No URL in API response")
    except Exception as e:
        print(f"[!] API try failed ({e}), trying page scrape...")
        page = requests.get(f"https://soravideo.com/?url={sora_link}", headers=headers, timeout=30)
        mp4_match = re.search(r'(https?://[^\s"\']+\.mp4[^\s"\']*)', page.text)
        if not mp4_match:
            raise Exception("Could not find download URL from soravideo.com")
        download_url = mp4_match.group(1)
    print(f"[↓] Downloading MP4...")
    with requests.get(download_url, stream=True, timeout=300) as r:
        r.raise_for_status()
        with open(output_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    print(f"[✓] Downloaded: {os.path.getsize(output_path)/1024/1024:.1f} MB")
    return output_path

def generate_title(sora_link):
    print("[🤖] Generating title with Claude AI...")
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
    url_hint = sora_link.split("/")[-1].replace("-", " ").replace("_", " ")
    msg = client.messages.create(
        model="claude-sonnet-4-20250514", max_tokens=500,
        messages=[{"role": "user", "content": f"""You are a YouTube title expert for an animal video channel.
Generate title and description for an AI animal video. URL hint: {url_hint}
Return ONLY valid JSON, no markdown:
{{"title": "Catchy title under 60 chars with emoji", "description": "2-3 lines description with hashtags at end.", "tags": ["animals","wildlife","nature","cute","AI animals"]}}"""}]
    )
    text = msg.content[0].text.strip()
    text = re.sub(r'^```json\s*', '', text); text = re.sub(r'\s*```$', '', text)
    data = json.loads(text)
    print(f"[✓] Title: {data['title']}")
    return data

def upload_to_youtube(youtube, video_path, title, description, tags):
    print(f"[↑] Uploading: {title}")
    body = {"snippet": {"title": title, "description": description, "tags": tags, "categoryId": "15"},
            "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}}
    media = MediaFileUpload(video_path, mimetype="video/mp4", resumable=True, chunksize=1024*1024*5)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"[↑] {int(status.progress()*100)}%")
    print(f"[✓] Done! https://youtube.com/watch?v={response['id']}")
    return response["id"]

def main():
    print(f"\n{'='*50}\nYT Auto Uploader — {datetime.now().strftime('%Y-%m-%d %H:%M')} UTC\n{'='*50}\n")
    with open(VIDEOS_JSON) as f:
        data = json.load(f)
    videos = data.get("videos", [])
    pending = [v for v in videos if v.get("status") == "pending"]
    print(f"[i] Pending: {len(pending)}")
    if not pending:
        print("[!] Nothing to upload."); return
    video = pending[0]
    print(f"[→] Processing: {video['link']}")
    try:
        path = download_video(video["link"])
        meta = generate_title(video["link"])
        yt = get_youtube_service()
        yt_id = upload_to_youtube(yt, path, meta["title"], meta["description"], meta.get("tags", []))
        for v in videos:
            if v["id"] == video["id"]:
                v["status"] = "done"; v["youtubeId"] = yt_id
                v["uploadedAt"] = datetime.now(timezone.utc).isoformat()
                v["title"] = meta["title"]; break
        if os.path.exists(path): os.remove(path)
        print(f"\n[✅] SUCCESS!")
    except Exception as e:
        print(f"\n[❌] ERROR: {e}")
        for v in videos:
            if v["id"] == video["id"]:
                v["status"] = "failed"; v["error"] = str(e); break
        sys.exit(1)
    finally:
        with open(VIDEOS_JSON, "w") as f:
            json.dump({"videos": videos}, f, indent=2)

if __name__ == "__main__":
    main()
