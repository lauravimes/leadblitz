#!/usr/bin/env python3
"""
Absolute minimal test - just HTTP server
"""
import os
from http.server import HTTPServer, BaseHTTPRequestHandler

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'Hello! LeadBlitz basic test working!')
    
    def log_message(self, format, *args):
        return  # Suppress logs

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    server = HTTPServer(('0.0.0.0', port), Handler)
    print(f"Server starting on port {port}")
    server.serve_forever()