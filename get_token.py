"""
Ek baar apne PC par run karo — YouTube refresh token milega.
  pip install google-auth-oauthlib google-api-python-client
  python get_token.py
"""
import json, os
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
print("\n" + "="*50 + "\n  YouTube Token Generator\n" + "="*50)
client_id = input("\nGOOGLE CLIENT_ID paste karo: ").strip()
client_secret = input("GOOGLE CLIENT_SECRET paste karo: ").strip()

config = {"installed": {"client_id": client_id, "client_secret": client_secret,
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"]}}

with open("temp_client.json", "w") as f: json.dump(config, f)
print("\n[→] Browser mein YouTube channel wale account se login karo...\n")
flow = InstalledAppFlow.from_client_secrets_file("temp_client.json", SCOPES)
creds = flow.run_local_server(port=0)
os.remove("temp_client.json")

print("\n" + "="*50)
print("  GitHub Secrets mein yeh 3 values add karo:")
print("="*50)
print(f"\nYOUTUBE_CLIENT_ID      = {client_id}")
print(f"YOUTUBE_CLIENT_SECRET  = {client_secret}")
print(f"YOUTUBE_REFRESH_TOKEN  = {creds.refresh_token}\n")

with open("my_tokens.txt", "w") as f:
    f.write(f"YOUTUBE_CLIENT_ID={client_id}\n")
    f.write(f"YOUTUBE_CLIENT_SECRET={client_secret}\n")
    f.write(f"YOUTUBE_REFRESH_TOKEN={creds.refresh_token}\n")
print("(Backup: my_tokens.txt mein save ho gaye)\n")
