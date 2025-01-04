# Email Account Scanner

A Python tool for analyzing your email inbox to discover and track your digital footprint. This tool helps you identify services and accounts linked to your email address, track personalized communications, and analyze email marketing patterns.

## Features

- Scans email inbox for specified time periods (default: 6 months)
- Identifies linked services and accounts across multiple categories:
  - Social Media
  - Shopping
  - Finance
  - Cloud Services
  - Subscription Services
  - Gaming
  - Professional
  - Travel
- Detects personalized emails using your name
- Tracks email marketing and analytics elements
- Maintains history of scanned emails to avoid duplicates
- Generates detailed reports of findings
- Supports multiple email encoding formats
- Compatible with Gmail and other IMAP servers

## Prerequisites

- Python 3.6 or higher
- Access to an email account via IMAP
- For Gmail users: App Password if 2FA is enabled

## Required Python Packages

```bash
pip install imaplib-ext
```

## Installation

1. Clone this repository or download the script:
```bash
git clone [repository-url]
cd email-scanner
```

2. Make sure you have the required Python packages installed

## Configuration

Before running the scanner, you need to configure the following in the `main()` function:

```python
email_address = "your.email@gmail.com"    # Your email address
password = "your-app-password-here"       # Your password/app password
name_to_scan = "Your Name"                # Your name to scan for
months_to_scan = 12                       # Number of months to scan
```

### Gmail-Specific Setup

If you're using Gmail with 2-Factor Authentication:
1. Go to your Google Account settings
2. Navigate to Security → App passwords
3. Generate an app password for this script
4. Use that app password instead of your regular password

## Usage

Run the script from the command line:

```bash
python email_scanner.py
```

The script will:
1. Connect to your email server
2. Scan emails from the specified period
3. Generate a report of findings
4. Save results to a timestamped file
5. Maintain a record of previously scanned emails

## Output Files

The script generates two types of output files:

1. `email_scan_results_[TIMESTAMP].txt`
   - Contains detailed scan results
   - Lists discovered services and accounts
   - Shows personalized senders

2. `previously_scanned.txt`
   - Maintains record of scanned emails
   - Used to avoid duplicate scanning
   - Updated after each successful scan

## Sample Output Structure

```
=== Email Account Scanner Report ===
Scanned email: your.email@gmail.com
Scanning for name: Your Name
Skipped X previously scanned emails

Senders using your name:
  - sender1@example.com
  - sender2@example.com

Found accounts by category:
Social Media:
  - facebook
  - twitter
Shopping:
  - amazon
  - ebay
...
```

## Privacy and Security Notes

- The script runs locally on your machine
- No data is sent to external servers
- Credentials are used only for IMAP connection
- All scan results are stored locally
- The script does not modify or delete any emails

## Limitations

- Only scans the inbox folder
- Requires IMAP access to be enabled
- May be limited by email provider's IMAP restrictions
- Processing time increases with the number of emails
- Some email encodings might not be properly decoded

## Error Handling

The script includes error handling for:
- Connection failures
- Login errors
- Email decoding issues
- File operations
- Content processing errors

## Contributing

Feel free to fork this repository and submit pull requests for any improvements. Some areas that could be enhanced:

- Add support for other email folders
- Implement multiprocessing for faster scanning
- Add more account patterns and categories
- Improve email content parsing
- Add export options in different formats

## License

[Add your chosen license here]

## Disclaimer

This tool is for personal use in analyzing your own email accounts. Be sure to comply with your email provider's terms of service and any applicable privacy laws.