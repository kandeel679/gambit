import http.server
import socketserver
import json
import os
import glob
import urllib.parse
import mimetypes

PORT = 8080
DIRECTORY = os.path.dirname(os.path.abspath(__file__))
GUI_STATIC_DIR = os.path.join(DIRECTORY, "gui_static")

class LogHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=GUI_STATIC_DIR, **kwargs)

    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path

        # Custom API Route for getting a list of logs
        if path == "/api/logs":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            
            # Find all markdown test reports
            log_files = glob.glob(os.path.join(DIRECTORY, "report_session_*.md"))
            
            # We also get file modification times to sort them newest first
            files_data = []
            for f in log_files:
                basename = os.path.basename(f)
                mtime = os.path.getmtime(f)
                files_data.append({
                    "filename": basename,
                    "mtime": mtime
                })
            
            files_data.sort(key=lambda x: x["mtime"], reverse=True)
            self.wfile.write(json.dumps(files_data).encode("utf-8"))
            return

        # Custom API Route for getting the content of a specific log
        elif path.startswith("/api/logs/"):
            filename = path.replace("/api/logs/", "")
            filename = urllib.parse.unquote(filename)
            file_path = os.path.join(DIRECTORY, filename)
            
            # Basic security check
            if not filename.startswith("report_session_") or not filename.endswith(".md") or not os.path.isfile(file_path):
                self.send_error(404, "File Not Found")
                return

            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            
            with open(file_path, "r", encoding="utf-8") as f:
                self.wfile.write(f.read().encode("utf-8"))
            return
            
        # Default route serves index.html or other static files
        if path == "/":
            self.path = "/index.html"
            
        return super().do_GET()

def run():
    Handler = LogHandler
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"[*] Gambit Log Analyzer GUI running at http://localhost:{PORT}")
        print("[*] Press Ctrl+C to stop")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server.")

if __name__ == "__main__":
    run()
