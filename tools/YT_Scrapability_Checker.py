import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi

def check_playlist(url):
    print(f"Checking {url}...")
    with yt_dlp.YoutubeDL({'quiet': True, 'extract_flat': True}) as ydl:
        info = ydl.extract_info(url, download=False)
        ids = [e['id'] for e in info.get('entries', [])]
    
    scratpable = 0
    for vid in ids:
        try:
            YouTubeTranscriptApi.list_transcripts(vid)
            scratpable += 1
        except: pass
    
    print(f"Result: {scratpable} out of {len(ids)} videos have transcripts.")

# Paste your playlist URL here
check_playlist("https://youtube.com/playlist?list=PLfskuxO2qb-nrfg-9pSeBe-mfnJkurqcc&si=HCQ6LEtkIqHPyE_2")