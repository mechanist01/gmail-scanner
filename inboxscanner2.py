import imaplib
import email
import re
from collections import defaultdict
from datetime import datetime, timedelta

class EmailScanner:
    def __init__(self, email_address, password, name_to_scan, imap_server="imap.gmail.com"):
        self.email_address = email_address
        self.password = password
        self.imap_server = imap_server
        self.name_to_scan = name_to_scan.lower()  # Name to look for in emails
        self.accounts = defaultdict(set)
        self.personalized_senders = set()  # Track senders using your name
        self.previously_scanned = self._load_previous_scans()  # Load previous scans
        self.skipped_count = 0  # Track number of skipped emails
        
    def connect(self):
        """Establish connection to the IMAP server"""
        try:
            # Ensure email and password are properly encoded
            self.email_address = self.email_address.encode('ascii', 'ignore').decode('ascii')
            self.password = self.password.encode('ascii', 'ignore').decode('ascii')
            
            # Create connection
            self.mail = imaplib.IMAP4_SSL(self.imap_server)
            
            try:
                self.mail.login(self.email_address, self.password)
                return True
            except imaplib.IMAP4.error as e:
                print(f"Login failed: {str(e)}")
                print("For Gmail, make sure you're using an App Password if 2FA is enabled")
                return False
                
        except Exception as e:
            print(f"Connection error: {str(e)}")
            print("Debug info:")
            print(f"Server: {self.imap_server}")
            print(f"Email: {self.email_address}")
            return False

    def scan_emails(self, months_back=6):
        """Scan emails for the specified period"""
        if not hasattr(self, 'mail'):
            print("Not connected to email server")
            return

        # Calculate date for search
        date = (datetime.now() - timedelta(days=30 * months_back)).strftime("%d-%b-%Y")
        
        self.mail.select('inbox')
        _, messages = self.mail.search(None, f'(SINCE {date})')
        email_ids = messages[0].split()
        total_emails = len(email_ids)
        
        print(f"\nFound {total_emails} emails to scan from the past {months_back} months")
        print("Starting scan...\n")
        
        for index, msg_num in enumerate(email_ids, 1):
            try:
                # Update progress
                progress = (index / total_emails) * 100
                print(f"\rProgress: {index}/{total_emails} emails scanned ({progress:.1f}%)", end="", flush=True)
                
                _, msg_data = self.mail.fetch(msg_num, '(RFC822)')
                email_body = msg_data[0][1]
                email_message = email.message_from_bytes(email_body)
                
                # Extract sender domain with proper decoding
                from_header = self._decode_header(email_message['from'])
                if from_header:
                    # Check if we've seen this sender before
                    if from_header in self.previously_scanned:
                        self.skipped_count += 1
                        continue
                        
                    domain = re.search('@[\w.-]+', from_header)
                    if domain:
                        domain_str = domain.group().strip('@')
                        if domain_str in self.previously_scanned:
                            self.skipped_count += 1
                            continue
                        self.accounts['Sender Domains'].add(domain_str)
                
                # Look for common account-related keywords in subject
                subject = email_message['subject']
                if subject:
                    if any(keyword in subject.lower() for keyword in ['account', 'subscription', 'login', 'welcome']):
                        self.accounts['Potential Accounts'].add(from_header)
                
                # Process email body
                self._process_content(email_message)
                
            except Exception as e:
                print(f"Error processing message: {str(e)}")
                continue

    def _load_previous_scans(self):
        """Load previously scanned senders and accounts from file"""
        try:
            with open('previously_scanned.txt', 'r', encoding='utf-8') as f:
                return set(line.strip() for line in f if line.strip())
        except FileNotFoundError:
            return set()

    def _save_previous_scans(self):
        """Save all scanned senders and accounts to file"""
        # Combine all unique identifiers
        all_items = set()
        
        # Add email senders
        all_items.update(self.personalized_senders)
        
        # Add all account identifiers
        for items in self.accounts.values():
            all_items.update(items)
            
        # Add sender domains
        if 'Sender Domains' in self.accounts:
            all_items.update(self.accounts['Sender Domains'])
        
        # Add to existing scans and save
        all_items.update(self.previously_scanned)
        
        with open('previously_scanned.txt', 'w', encoding='utf-8') as f:
            for item in sorted(all_items):
                f.write(f"{item}\n")

    def _decode_header(self, header_content):
        """Safely decode email header"""
        if not header_content:
            return ""
        try:
            # Try different encodings
            for encoding in ['utf-8', 'latin1', 'ascii', 'iso-8859-1']:
                try:
                    if isinstance(header_content, bytes):
                        return header_content.decode(encoding)
                    return str(header_content)
                except:
                    continue
            return str(header_content)  # fallback
        except:
            return ""

    def _decode_content(self, content):
        """Safely decode email content"""
        if not content:
            return ""
        try:
            if isinstance(content, bytes):
                # Try different encodings
                for encoding in ['utf-8', 'latin1', 'ascii', 'iso-8859-1', 'cp1252']:
                    try:
                        return content.decode(encoding)
                    except:
                        continue
            return str(content)
        except:
            return ""

    def _process_content(self, email_message):
        """Process email content for account indicators and personalization"""
        sender = self._decode_header(email_message['from'])
        subject = self._decode_header(email_message['subject'])
        
        # Check for personalization in subject
        if self.name_to_scan in subject.lower():
            if sender:
                self.personalized_senders.add(sender)

        for part in email_message.walk():
            if part.get_content_type() == "text/plain":
                try:
                    content = part.get_payload(decode=True)
                    decoded_content = self._decode_content(content)
                    if decoded_content:
                        self._find_accounts(decoded_content)
                        self._find_personalization(decoded_content, sender)
                except Exception as e:
                    print(f"Error processing email content: {str(e)}")
                    continue
                
    def _find_accounts(self, content):
        """Extract potential account information from content"""
        # Common account-related patterns
        patterns = {
            'Social Media': r'(?i)(facebook|twitter|instagram|linkedin|tiktok|reddit|snapchat|pinterest)',
            'Shopping': r'(?i)(amazon|ebay|etsy|shopify|walmart|target|bestbuy|aliexpress)',
            'Finance': r'(?i)(paypal|stripe|bank|credit|venmo|cashapp|wise|coinbase|crypto)',
            'Cloud Services': r'(?i)(google|dropbox|icloud|onedrive|box|mega|protonmail)',
            'Subscription Services': r'(?i)(netflix|spotify|hulu|disney|prime|youtube|paramount|peacock|apple)',
            'Gaming': r'(?i)(steam|epic|origin|uplay|psn|xbox|nintendo|battlenet)',
            'Professional': r'(?i)(slack|zoom|teams|asana|jira|trello|github|gitlab)',
            'Travel': r'(?i)(airbnb|booking|expedia|uber|lyft|airlines|hotel)'
        }
        
        for category, pattern in patterns.items():
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                self.accounts[category].add(match.group())

    def _find_personalization(self, content, sender):
        """Look for instances of name being used in content"""
        if self.name_to_scan in content.lower():
            if sender:
                self.personalized_senders.add(sender)

    def _find_tracking_elements(self, content):
        """Identify common tracking and analytics patterns"""
        tracking_patterns = {
            'Analytics': r'(?i)(google-analytics|gtag|analytics|pixel)',
            'Marketing': r'(?i)(mailchimp|sendgrid|constant\s*contact|campaign\s*monitor)',
            'Tracking IDs': r'(?i)(tracking[-_\s]*id|customer[-_\s]*id|user[-_\s]*id)',
            'Unsubscribe': r'(?i)(unsubscribe|opt[-_\s]*out|email[-_\s]*preferences)',
        }
        
        for category, pattern in tracking_patterns.items():
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                self.tracking_elements[category].add(match.group())

    def _analyze_html_content(self, html_content):
        """Analyze HTML content for tracking elements"""
        tracking_patterns = {
            'Tracking Pixels': r'(?i)<img[^>]+(?:tracking|pixel|analytics)[^>]+>',
            'External Scripts': r'(?i)<script[^>]+src=["\']([^"\']+)',
            'UTM Parameters': r'(?i)utm_[a-z]+=[^&\s]+',
            'Click Tracking': r'(?i)(?:click|link)[-_\s]*track',
        }
        
        for category, pattern in tracking_patterns.items():
            matches = re.finditer(pattern, html_content, re.IGNORECASE)
            for match in matches:
                self.tracking_elements[category].add(match.group())

    def _analyze_header(self, header_name, header_value):
        """Analyze email headers for tracking and list information"""
        header_patterns = {
            'List Headers': r'(?i)(list-|bounce-|return-path)',
            'Campaign IDs': r'(?i)(campaign[-_\s]*id|message[-_\s]*id)',
            'Marketing': r'(?i)(mailchimp|sendgrid|salesforce|marketo)',
        }
        
        for category, pattern in header_patterns.items():
            if re.search(pattern, f"{header_name}: {header_value}", re.IGNORECASE):
                self.tracking_elements[category].add(f"{header_name}: {header_value}")

    def generate_report(self):
        """Generate a formatted report of found accounts and tracking elements"""
        report = []
        report.append("=== Email Account Scanner Report ===")
        report.append(f"Scanned email: {self.email_address}")
        report.append(f"Scanning for name: {self.name_to_scan}")
        report.append(f"Skipped {self.skipped_count} previously scanned emails\n")
        
        # Report personalized senders
        if self.personalized_senders:
            report.append("Senders using your name:")
            for sender in sorted(self.personalized_senders):
                report.append(f"  - {sender}")
            report.append("")
        
        # Report accounts by category
        report.append("Found accounts by category:")
        for category, items in self.accounts.items():
            if items:
                report.append(f"{category}:")
                for item in sorted(items):
                    report.append(f"  - {item}")
                report.append("")
        
        # Report tracking elements
        if self.tracking_elements:
            report.append("Tracking and Marketing Elements:")
            for category, items in self.tracking_elements.items():
                if items:
                    report.append(f"{category}:")
                    for item in sorted(items):
                        report.append(f"  - {item}")
                    report.append("")
        
        return "\n".join(report)

    def close(self):
        """Close the IMAP connection"""
        if hasattr(self, 'mail'):
            self.mail.close()
            self.mail.logout()

    def save_to_file(self):
        """Save findings to a text file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"email_scan_results_{timestamp}.txt"
        
        with open(filename, 'w', encoding='utf-8') as f:
            # Write personalized senders
            f.write("=== SENDERS USING YOUR NAME ===\n")
            for sender in sorted(self.personalized_senders):
                f.write(f"{sender}\n")
            f.write("\n")
            
            # Write all discovered accounts/services
            f.write("=== DISCOVERED SERVICES AND ACCOUNTS ===\n")
            all_services = set()
            
            # Collect all unique services
            for items in self.accounts.values():
                all_services.update(items)
            
            # Write each service on a new line
            for service in sorted(all_services):
                f.write(f"{service}\n")
            
            print(f"\nResults have been saved to: {filename}")

def main():
    # Configuration
    email_address = "______________"  # Replace with your email
    password = "_____________"     # Replace with your password/app password
    name_to_scan = "______________"             # Replace with your name to scan for
    months_to_scan = 12                    # Number of months of emails to scan
    
    scanner = EmailScanner(email_address, password, name_to_scan)
    
    if scanner.connect():
        print(f"\nStarting email scan process for the past {months_to_scan} months...")
        scanner.scan_emails(months_back=months_to_scan)  # Pass the months parameter to scan_emails
        print("\n\nScan complete! Saving results...")
        scanner.save_to_file()
        scanner._save_previous_scans()  # Save scanned items for future runs
        scanner.close()
        print("\nProcess finished!")
    else:
        print("Failed to connect to email server.")
    
if __name__ == "__main__":
    main()