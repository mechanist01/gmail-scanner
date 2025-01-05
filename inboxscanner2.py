import imaplib
import email
import re
import csv
import argparse
from collections import defaultdict
from datetime import datetime, timedelta
from urllib.parse import parse_qs, urlparse
from typing import Dict, Set, Tuple
from email.utils import parseaddr


class EmailScanner:
    def __init__(self, email_address, password, name_to_scan, imap_server="imap.gmail.com"):
        self.email_address = email_address
        self.password = password
        self.imap_server = imap_server
        self.name_to_scan = name_to_scan.lower()
        # Track email frequency by domain and sender
        self.domain_data = defaultdict(lambda: {
            'senders': defaultdict(int),          # Track frequency per sender
            'categories': set(),                  # Track categories this domain belongs to
            'unsubscribe_data': {},              # Store unsubscribe data
            'list_unsubscribe': False,           # Track List-Unsubscribe header presence
            'unsubscribe_urls': set(),           # Store HTTP unsubscribe URLs
            'unsubscribe_mailtos': set(),        # Store mailto unsubscribe addresses
            'last_unsubscribe_header': None      # Store the full unsubscribe header
        })

    def connect(self):
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
                    # Process sender information
                    self._process_sender(from_header)
                    
                    # Check for List-Unsubscribe header
                    domain = self._extract_domain_from_email(from_header)
                    if email_message.get('List-Unsubscribe'):
                        unsubscribe_header = email_message.get('List-Unsubscribe')
                        self.domain_data[domain]['list_unsubscribe'] = True
                        self.domain_data[domain]['last_unsubscribe_header'] = unsubscribe_header
                        self._store_unsubscribe_info(unsubscribe_header, domain)
                
                # Process email body
                self._process_content(email_message)
                
            except Exception as e:
                print(f"Error processing message: {str(e)}")
                continue

    def _store_unsubscribe_info(self, header, domain):
        """Parse and store unsubscribe URLs and mailto addresses"""
        try:
            urls = re.findall(r'<(https?://[^>]+)>', header)
            mailtos = re.findall(r'<mailto:([^>]+)>', header)
            
            if urls:
                self.domain_data[domain]['unsubscribe_urls'].update(urls)
            if mailtos:
                self.domain_data[domain]['unsubscribe_mailtos'].update(mailtos)
        except Exception as e:
            print(f"Error storing unsubscribe info: {str(e)}")

    def _extract_domain_from_email(self, email_str: str) -> str:
        try:
            # First try to parse as email address
            _, email_addr = parseaddr(email_str)
            if '@' in email_addr:
                return email_addr.split('@')[1].lower()
            
            # If not email, try to find domain in string
            domain_match = re.search(r'@([\w.-]+)', email_str)
            if domain_match:
                return domain_match.group(1).lower()
            
            # If still no match, try to extract domain-like string
            domain_pattern = r'(?:https?://)?(?:www\.)?([\w.-]+(?:\.(?:com|org|net|edu|gov|io|ai|app|co|us|uk|de|fr|es|it|nl|ru|cn|jp|br|au|ca|ch|se|no|dk|fi|pl|cz|hu|ro|bg|gr|pt|ie|be|at|sk|hr|rs|si|ee|lv|lt|by|ua|md|tr|il|sa|ae|qa|eg|za|in|pk|bd|th|vn|id|ph|my|sg|kr|tw|hk|nz)))'
            domain_match = re.search(domain_pattern, email_str)
            if domain_match:
                return domain_match.group(1).lower()
            
        except Exception as e:
            print(f"Error extracting domain from {email_str}: {str(e)}")
        
        return email_str.lower()  # Return original string as fallback

    def _normalize_service_name(self, service: str) -> str:
        service = service.lower()
        
        # Common service name mappings
        service_mappings = {
            'google': ['gmail', 'googlemail'],
            'microsoft': ['outlook', 'hotmail', 'live'],
            'meta': ['facebook', 'instagram', 'whatsapp'],
            'amazon': ['aws', 'prime'],
            'zoom': ['zoominfo', 'zoomvideo'],
            'youtube': ['yt', 'youtu']
        }
        
        # Check if service is an alias and return the main name
        for main_service, aliases in service_mappings.items():
            if service in aliases:
                return main_service
                
        return service

    def _decode_header(self, header_content):
        if not header_content:
            return ""
        try:
            for encoding in ['utf-8', 'latin1', 'ascii', 'iso-8859-1']:
                try:
                    if isinstance(header_content, bytes):
                        return header_content.decode(encoding)
                    return str(header_content)
                except:
                    continue
            return str(header_content)
        except:
            return ""

    def _decode_content(self, content):
        if not content:
            return ""
        try:
            if isinstance(content, bytes):
                for encoding in ['utf-8', 'latin1', 'ascii', 'iso-8859-1', 'cp1252']:
                    try:
                        return content.decode(encoding)
                    except:
                        continue
            return str(content)
        except:
            return ""

    def _process_sender(self, from_header: str, category: str = None):
        domain = self._extract_domain_from_email(from_header)
        name, email_addr = parseaddr(from_header)
        
        # Update sender frequency
        self.domain_data[domain]['senders'][from_header] += 1
        
        # Add category if provided
        if category:
            self.domain_data[domain]['categories'].add(category)

    def _process_content(self, email_message):
        sender = self._decode_header(email_message['from'])
        
        if sender:
            self._process_sender(sender)
            
            # Check for List-Unsubscribe header
            domain = self._extract_domain_from_email(sender)
            if email_message.get('List-Unsubscribe'):
                unsubscribe_header = email_message.get('List-Unsubscribe')
                self.domain_data[domain]['list_unsubscribe'] = True
                self.domain_data[domain]['last_unsubscribe_header'] = unsubscribe_header
                self._store_unsubscribe_info(unsubscribe_header, domain)

        for part in email_message.walk():
            if part.get_content_type() in ["text/plain", "text/html"]:
                try:
                    content = part.get_payload(decode=True)
                    decoded_content = self._decode_content(content)
                    if decoded_content:
                        found_services = self._find_accounts(decoded_content)
                        for service_info in found_services:
                            service, category = service_info
                            self._extract_unsubscribe_info(email_message, decoded_content, service)
                            domain = self._extract_domain_from_email(service)
                            self.domain_data[domain]['categories'].add(category)
                except Exception as e:
                    print(f"Error processing email content: {str(e)}")
                    continue

    def _find_accounts(self, content):
        found_services = set()
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
                service = match.group()
                service = self._normalize_service_name(service)
                found_services.add((service, category))
                
        return found_services

    def _process_unsubscribe_url(self, url: str, service: str, timestamp: datetime):
        try:
            parsed_url = urlparse(url)
            query_params = parse_qs(parsed_url.query)
            
            # Extract potential token parameters
            token_params = ['token', 'id', 'uid', 'key', 'code', 'hash', 'verify']
            tokens = []
            
            for param in token_params:
                if param in query_params:
                    tokens.extend(query_params[param])
            
            # Get domain
            domain = self._extract_domain_from_email(service)
            
            # Store or update the unsubscribe data
            if url not in self.domain_data[domain]['unsubscribe_data']:
                self.domain_data[domain]['unsubscribe_data'][url] = (timestamp, tokens[0] if tokens else None)
            else:
                # Update only if new timestamp is more recent
                existing_timestamp, _ = self.domain_data[domain]['unsubscribe_data'][url]
                if timestamp > existing_timestamp:
                    self.domain_data[domain]['unsubscribe_data'][url] = (timestamp, tokens[0] if tokens else None)
                    
            # Add URL to unsubscribe_urls set
            self.domain_data[domain]['unsubscribe_urls'].add(url)
                    
        except Exception as e:
            print(f"Error processing unsubscribe URL: {str(e)}")

    def _extract_unsubscribe_info(self, email_message, content: str, service: str):
        timestamp = email.utils.parsedate_to_datetime(email_message['date']) if email_message['date'] else datetime.now()
        
        # Check List-Unsubscribe header
        list_unsubscribe = email_message.get('List-Unsubscribe', '')
        if list_unsubscribe:
            urls = re.findall(r'<(https?://[^>]+)>', list_unsubscribe)
            for url in urls:
                self._process_unsubscribe_url(url, service, timestamp)

        # Look for unsubscribe links in content
        unsubscribe_patterns = [
            r'(?i)https?://[^\s<>"]+(?:unsubscribe|opt-?out)[^\s<>"]*',
            r'(?i)https?://[^\s<>"]+(?:email-?preferences)[^\s<>"]*',
            r'(?i)https?://[^\s<>"]+(?:manage-?subscriptions)[^\s<>"]*'
        ]
        
        for pattern in unsubscribe_patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                self._process_unsubscribe_url(match.group(), service, timestamp)

    def save_to_file(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save domain data
        domains_filename = f"domain_analysis_{timestamp}.csv"
        with open(domains_filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            # Write header with new column order
            writer.writerow([
                'Delete',                # New empty column
                'List-Unsubscribe',      # List-Unsubscribe presence
                'Domain',
                'Categories',
                'Unique Senders',
                'Total Emails',
                'Sender List',
                'Unsubscribe URLs',      # New column
                'Unsubscribe Mailtos',   # New column
                'Unsubscribe Header',    # New column
                'Token',
                'Last Updated'
            ])
            
            # Process domains with more than 1 email
            for domain, data in sorted(self.domain_data.items()):
                total_emails = sum(data['senders'].values())
                if total_emails < 2:
                    continue
                
                # Get categories
                categories = '; '.join(sorted(data['categories'])) if data['categories'] else 'Uncategorized'
                
                # Get sender information
                sender_count = len(data['senders'])
                senders_list = '; '.join(data['senders'].keys())
                
                # Get most recent unsubscribe data
                token = "N/A"
                timestamp = "N/A"
                
                # Get unsubscribe URLs and mailtos
                unsubscribe_urls = '; '.join(sorted(data['unsubscribe_urls'])) if data['unsubscribe_urls'] else ''
                unsubscribe_mailtos = '; '.join(sorted(data['unsubscribe_mailtos'])) if data['unsubscribe_mailtos'] else ''
                unsubscribe_header = data['last_unsubscribe_header'] if data['last_unsubscribe_header'] else ''
                
                if data['unsubscribe_data']:
                    most_recent = max(data['unsubscribe_data'].items(), key=lambda x: x[1][0])
                    timestamp, token = most_recent[1]
                    token = token if token else "No token"
                
                # Write row with new column order
                writer.writerow([
                    '',  # Empty Delete column
                    'Yes' if data['list_unsubscribe'] else 'No',
                    domain,
                    categories,
                    sender_count,
                    total_emails,
                    senders_list,
                    unsubscribe_urls,
                    unsubscribe_mailtos,
                    unsubscribe_header,
                    token,
                    timestamp
                ])
        
        print(f"\nDomain analysis saved to: {domains_filename}")

    def close(self):
        if hasattr(self, 'mail'):
            self.mail.close()
            self.mail.logout()


def parse_arguments():
    parser = argparse.ArgumentParser(description='Email Account Scanner')
    parser.add_argument('-e', '--email', required=True, help='Email address to scan')
    parser.add_argument('-p', '--password', required=True, help='Email password or app password')
    parser.add_argument('-n', '--name', required=True, help='Name to scan for in emails')
    parser.add_argument('-m', '--months', type=int, default=12, help='Number of months to scan (default: 12)')
    parser.add_argument('-s', '--server', default='imap.gmail.com', help='IMAP server (default: imap.gmail.com)')
    
    args = parser.parse_args()
    args.password = args.password
    
    return args


def main():
    # Parse command line arguments
    args = parse_arguments()
    
    scanner = EmailScanner(args.email, args.password, args.name, args.server)
    
    if scanner.connect():
        print(f"\nStarting email scan process for the past {args.months} months...")
        scanner.scan_emails(months_back=args.months)
        print("\n\nScan complete! Saving results...")
        scanner.save_to_file()
        scanner.close()
        print("\nProcess finished!")
        print("Remember to delete your temporary Gmail app password if you used one!")
    else:
        print("Failed to connect to email server.")


if __name__ == "__main__":
    main() 