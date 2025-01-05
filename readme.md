# Email Account Scanner and Unsubscriber

A Python tool for analyzing your email inbox to discover and track your digital footprint, with the ability to automate unsubscribing from unwanted communications. This tool helps you identify services and accounts linked to your email address, track personalized communications, analyze email marketing patterns, and bulk unsubscribe from selected senders.

## Features

- Scans email inbox for specified time periods (default: 12 months)
- Groups communications by domain with frequency tracking
- Identifies linked services and accounts across multiple categories:
  - Social Media (Facebook, Twitter, Instagram, etc.)
  - Shopping (Amazon, eBay, Etsy, etc.)
  - Finance (PayPal, Stripe, banking, crypto)
  - Cloud Services (Google, Dropbox, iCloud)
  - Subscription Services (Netflix, Spotify, Disney+)
  - Gaming (Steam, Epic, PlayStation)
  - Professional (Slack, Zoom, GitHub)
  - Travel (Airbnb, Booking, Uber)
- Detects personalized emails using your name
- Extracts and tracks unsubscribe links with tokens
- Maintains history of scanned emails to avoid duplicates
- Generates detailed CSV reports for easy analysis
- Automated unsubscribe functionality for bulk email management
- Supports multiple email encoding formats
- Compatible with Gmail and other IMAP servers

## Prerequisites

- Python 3.6 or higher
- Access to an email account via IMAP
- For Gmail users: App Password if 2FA is enabled

## Required Python Packages

```bash
pip install imaplib requests
```

## Installation

1. Clone this repository or download the scripts:
```bash
git clone https://github.com/mechanist01/gmail-scanner
cd email-scanner
```

2. Make sure you have the required Python packages installed

## Email Scanner Usage

The scanner script uses command line arguments for configuration:

```bash
python inboxscanner2.py -e EMAIL -p PASSWORD -n NAME [-m MONTHS] [-s SERVER]
```

Arguments:
- `-e, --email`: Your email address (required)
- `-p, --password`: Your password or app password (required, use quotes if contains spaces)
- `-n, --name`: Your name to scan for (required)
- `-m, --months`: Number of months to scan (optional, default: 12)
- `-s, --server`: IMAP server (optional, default: imap.gmail.com)

Example:
```bash
# Basic usage with Gmail
python inboxscanner2.py -e your.email@gmail.com -p "your app password" -n "Your Name"
```

## Unsubscriber Usage

After running the scanner and generating the domain analysis CSV, you can use the unsubscriber to automatically process unsubscribe requests:

```bash
python unsubscriber.py -e EMAIL -p PASSWORD -c CSV_PATH [-s SERVER] [-d DAYS]
```

Arguments:
- `-e, --email`: Your email address (required)
- `-p, --password`: Your password or app password (required)
- `-c, --csv`: Path to the domain analysis CSV file (required)
- `-s, --server`: IMAP server (optional, default: imap.gmail.com)
- `-d, --days`: Number of days back to search for unsubscribe links (optional, default: 30)

Example:
```bash
python unsubscriber.py -e your.email@gmail.com -p "your app password" -c "domain_analysis_20250104_120530.csv"
```

### Preparing the CSV for Unsubscribing

The domain analysis CSV contains several columns that control the unsubscribe process:

1. `Delete`: Set this column to "yes" for domains you want to unsubscribe from
2. `List-Unsubscribe`: Automatically populated by the scanner, indicates if unsubscribe link is available
3. `Domain`: The email sender's domain

To prepare for unsubscribing:
1. Open the generated domain analysis CSV in your preferred spreadsheet software
2. Review the domains and their email frequencies
3. In the "Delete" column, enter "yes" for any domain you want to unsubscribe from
4. Save the CSV file
5. Run the unsubscribe script with the path to your modified CSV

Note: The unsubscriber will only process domains where both "Delete" is "yes" AND "List-Unsubscribe" is "yes"

### Gmail-Specific Setup

If you're using Gmail with 2-Factor Authentication:
1. Go to your Google Account settings
2. Navigate to Security → App passwords
3. Generate an app password for this script
4. Use that app password instead of your regular password
5. Important: After completing your unsubscribe operations, return to your Google Account settings and delete the temporary app password for security

## Output Files

The scripts generate several types of output files:

1. `personalized_senders_[TIMESTAMP].csv`
   - Columns: Sender Name, Email Address, Full Header
   - Lists all senders who used your name in communications

2. `domain_analysis_[TIMESTAMP].csv`
   - Columns: Domain, Categories, Unique Senders, Total Emails, Sender List, Unsubscribe URL, Token, Last Updated
   - Groups communications by domain
   - Shows categorization and frequency
   - Includes unsubscribe information
   - Only includes domains with 2+ emails

3. `unsubscribe_log_[TIMESTAMP].txt`
   - Detailed log of unsubscribe operations
   - Records successful and failed attempts
   - Timestamps for each operation
   - Error messages and debugging information

4. `previously_scanned.txt`
   - Maintains record of scanned emails
   - Used to avoid duplicate scanning
   - Updated after each successful scan

## Privacy and Security Notes

- The script runs locally on your machine
- No data is sent to external servers
- Credentials are used only for IMAP connection
- All scan results are stored locally
- The script does not modify or delete any emails
- App passwords should be deleted after use

## Limitations

- Only scans the inbox folder
- Requires IMAP access to be enabled
- May be limited by email provider's IMAP restrictions
- Processing time increases with the number of emails
- Some email encodings might not be properly decoded
- Some unsubscribe links may require manual intervention

## Error Handling

The script includes error handling for:
- Connection failures
- Login errors
- Email decoding issues
- File operations
- Content processing errors
- Password parsing with spaces
- Unsubscribe link failures
- Invalid CSV formatting
- Network timeouts

## Contributing

Feel free to fork this repository and submit pull requests for any improvements. Some areas that could be enhanced:

- Add support for other email folders
- Implement multiprocessing for faster scanning
- Add more account patterns and categories
- Improve email content parsing
- Add additional export formats
- Enhanced unsubscribe link detection
- Support for OAuth authentication
- Batch processing improvements
- Additional email provider support

## License

MIT License

Copyright (c) 2025

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## Security Reminder

After completing your email analysis and unsubscribe operations, remember to:
1. Delete any temporary app passwords created for this tool
2. Securely store or delete the generated CSV files containing your email analysis
3. Review the unsubscribe logs to confirm all operations completed as expected
4. Check your email settings to ensure IMAP access is still configured as desired
5. Monitor your inbox for any confirmation emails from unsubscribe operations

## Disclaimer

This tool is for personal use in analyzing your own email accounts. Be sure to comply with your email provider's terms of service and any applicable privacy laws. The unsubscribe functionality should be used responsibly and in accordance with email marketing regulations.
