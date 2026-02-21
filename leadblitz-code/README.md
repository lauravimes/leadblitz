# AI Lead Generation Tool

A full-stack web application for entrepreneurs who build AI-powered websites and automation services. Find, score, and contact local businesses that could benefit from modern web presence and AI tools.

## 🚀 Quick Start

### 1. Set Up Environment Variables

Create a `.env` file in the root directory with your API keys:

```bash
GOOGLE_MAPS_API_KEY=your_google_maps_api_key
SENDGRID_API_KEY=your_sendgrid_api_key
FROM_EMAIL=your_verified_sender_email@example.com
OPENAI_API_KEY=your_openai_api_key
```

### 2. Get Your API Keys

- **Google Maps API**: [Get key](https://developers.google.com/maps/documentation/places/web-service/get-api-key) - Enable "Places API"
- **SendGrid API**: [Get key](https://sendgrid.com/solutions/email-api/) - Verify your sender email
- **OpenAI API**: [Get key](https://platform.openai.com/api-keys) - Uses GPT-3.5-turbo

### 3. Run the Application

The app is already running! Just add your environment variables in Replit's Secrets panel:
- Click the lock icon (🔒) in the sidebar
- Add each variable (GOOGLE_MAPS_API_KEY, SENDGRID_API_KEY, FROM_EMAIL, OPENAI_API_KEY)
- The server will automatically restart

Visit your app URL to access the dashboard.

## ✨ Features

### 1. **Lead Discovery**
- Search local businesses by type and location
- Uses official Google Places API (compliant, no scraping)
- Automatically extracts: name, address, phone, website
- Capped at 50 results per search to respect API limits

### 2. **AI-Powered Scoring**
- Analyzes website quality (SSL, mobile responsiveness, technology stack)
- OpenAI generates 0-100 opportunity score
- Identifies high-value leads (score ≥70)
- Evaluates potential for AI/automation improvements

### 3. **CRM Pipeline**
- 6-stage pipeline: New → Contacted → Replied → Meeting → Closed Won/Lost
- Inline editing for email addresses and notes
- Click-to-select leads for personalization
- Real-time analytics dashboard

### 4. **Email Composer**
- Template system with variables: `{{business_name}}`, `{{city}}`, `{{score}}`, etc.
- Preview first 5 emails before sending
- AI-powered personalization per lead
- Automatic unsubscribe footer included

### 5. **Bulk Email Sending**
- Filter by minimum score threshold
- Filter by pipeline stage
- SendGrid integration for reliable delivery
- Automatic stage update to "Contacted"
- Detailed error tracking

### 6. **Analytics & Export**
- Total leads and high-opportunity count
- Emails sent tracking
- Deals in progress visualization
- Pipeline distribution chart
- CSV export for all leads

## 📋 How to Use

### Finding Leads
1. Enter a business type (e.g., "dentist", "cafe", "plumber")
2. Enter a location (e.g., "Leeds, UK", "New York, NY")
3. Click "Search Leads"
4. Leads are saved automatically

### Scoring Leads
1. After searching, click "Score All Leads with AI"
2. The system analyzes each website and assigns a score
3. High scores (≥70) indicate strong opportunities

### Managing Leads
- **Add Email**: Click on "Add email..." in the table
- **Change Stage**: Use the dropdown in the Stage column
- **Add Notes**: Click on "Add notes..." to track details
- **Select for AI**: Click any row to select it for personalized email generation

### Sending Emails
1. Create templates in the Email Composer section
2. Use variables like `{{business_name}}`, `{{city}}`, `{{score}}`
3. Preview emails to check formatting
4. Optionally: Generate AI-personalized emails for specific leads
5. Set filters (minimum score, stage)
6. Click "Send Bulk Emails"

## 🛡️ Compliance & Safety

This tool is designed for **responsible outreach only**:

- ✅ Uses official APIs (no web scraping)
- ✅ Includes unsubscribe messaging in emails
- ✅ Prominent compliance notice in UI
- ✅ Encourages permission-based marketing

**Important**: Only contact businesses where you have a legitimate interest and comply with:
- GDPR (EU)
- PECR (UK)
- CAN-SPAM (US)
- Other local regulations

## 🏗️ Technical Architecture

### Backend
- **Framework**: FastAPI (Python)
- **Server**: Uvicorn
- **Database**: In-memory (easily migrated to PostgreSQL)
- **APIs**: Google Places, OpenAI, SendGrid

### Frontend
- **Pure vanilla JavaScript** (no frameworks)
- **Responsive CSS** with dark theme
- **Real-time updates** via API calls

### Project Structure
```
.
├── main.py              # FastAPI application
├── helpers/
│   ├── database.py      # In-memory lead storage
│   ├── google_places.py # Google Places API integration
│   ├── enrichment.py    # Website analysis & AI scoring
│   ├── email_service.py # SendGrid email functions
│   └── ai_email.py      # OpenAI email personalization
├── static/
│   ├── index.html       # Dashboard UI
│   ├── styles.css       # Dark theme styling
│   └── app.js           # Frontend logic
└── requirements.txt     # Python dependencies
```

## 🔧 Configuration

All configuration is via environment variables:

| Variable | Description | Required |
|----------|-------------|----------|
| `GOOGLE_MAPS_API_KEY` | Google Places API key | Yes (for search) |
| `OPENAI_API_KEY` | OpenAI API key | Yes (for AI features) |
| `SENDGRID_API_KEY` | SendGrid API key | Yes (for emails) |
| `FROM_EMAIL` | Verified sender email | Yes (for emails) |

## 📊 API Endpoints

- `POST /api/search` - Search for businesses
- `POST /api/score-leads` - AI score all leads
- `GET /api/leads` - Get all leads
- `PATCH /api/leads/{id}` - Update a lead
- `GET /api/export` - Download CSV
- `POST /api/preview-emails` - Preview rendered emails
- `POST /api/generate-personalized` - AI generate email
- `POST /api/send-emails` - Send bulk emails
- `GET /api/analytics` - Get analytics data

## 🚀 Deployment

This app is ready to deploy on Replit:
1. Add your environment variables in Secrets
2. Click the "Deploy" button in Replit
3. Your app will be live with a public URL

## 🔮 Future Enhancements

- PostgreSQL database for persistence
- Email reply tracking via webhooks  
- Advanced filtering and search
- Campaign performance metrics (open rates, clicks)
- Batch CSV import
- Multiple campaigns support
- Team collaboration features

## 📝 License

This project is provided as-is for educational and commercial use.

## ⚠️ Disclaimer

This tool is designed for legitimate business outreach. Users are responsible for:
- Obtaining necessary permissions
- Complying with anti-spam laws
- Following email marketing best practices
- Respecting opt-out requests

---

**Built with ❤️ for entrepreneurs scaling their AI services business**
