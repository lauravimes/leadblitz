#!/bin/bash
# himalaya-send wrapper: sends email with attachment via himalaya MML format
# Usage: himalaya-send.sh <to> <subject> <body_html> <attachment_path>

TO="$1"
SUBJECT="$2"
BODY_HTML="$3"
ATTACHMENT="$4"

if [ -z "$TO" ] || [ -z "$SUBJECT" ] || [ -z "$BODY_HTML" ]; then
  echo "Usage: himalaya-send.sh <to> <subject> <body_html> [attachment_path]"
  exit 1
fi

# Build MML message
MSG="From: Laura Vimes <laura.vimes@icloud.com>
To: ${TO}
Subject: ${SUBJECT}

<#part type=text/html>
${BODY_HTML}
</#part>"

if [ -n "$ATTACHMENT" ] && [ -f "$ATTACHMENT" ]; then
  FILENAME=$(basename "$ATTACHMENT")
  MSG="${MSG}
<#part filename=${FILENAME} type=application/pdf>
$(base64 < "$ATTACHMENT")
</#part>"
fi

echo "$MSG" | himalaya message send
