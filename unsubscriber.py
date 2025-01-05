import imaplib
import email
import csv
import argparse
import re
import requests
import smtplib
import logging
import sys
from datetime import datetime, timedelta
from email.utils import parseaddr
from urllib.parse import unquote, parse_qs, urlparse
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


class UnsubscribeAutomation:
    def __init__(self, email_address, password, imap_server="imap.gmail.com", smtp_server="smtp.gmail.com", smtp_port=587):
        self.email_address = email_address
        self.password = password
        self.imap_server = imap_server
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.mail = None
        self.smtp = None
        self.processed_domains = set()
        self.setup_logging()

    def setup_logging(self):
         
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"unsubscribe_log_{timestamp}.txt"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_filename),
                logging.StreamHandler(sys.stdout)
            ]
        )
        logging.info("Starting unsubscribe automation")

    def connect(self):
         
        try:
            logging.info(f"Connecting to IMAP server: {self.imap_server}")
            self.mail = imaplib.IMAP4_SSL(self.imap_server)
            self.mail.login(self.email_address, self.password)
            logging.info("IMAP connection successful")
            
            logging.info(f"Connecting to SMTP server: {self.smtp_server}")
            self.smtp = smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=30)
            self.smtp.starttls()
            self.smtp.login(self.email_address, self.password)
            logging.info("SMTP connection successful")
            
            return True
        except Exception as e:
            logging.error(f"Connection error: {str(e)}")
            return False

    def decode_header_string(self, header):
         
        logging.info("Decoding header string")
        try:
 
            header = ' '.join(header.split())
            
 
            decoded = ''
            parts = re.findall(r'=\?us-ascii\?Q\?(.*?)\?=', header)
            
            if parts:
 
                encoded = ''.join(parts)
                
 
                decoded = encoded.replace('=3D', '=')
                decoded = decoded.replace('=3F', '?')
                decoded = decoded.replace('=2E', '.')
                decoded = decoded.replace('=2F', '/')
                decoded = decoded.replace('=5F', '_')
                decoded = decoded.replace('=2D', '-')
                decoded = decoded.replace('=3C', '<')
                decoded = decoded.replace('=3E', '>')
                decoded = decoded.replace('=40', '@')
                decoded = unquote(decoded)
            else:
                decoded = header
                
            logging.info(f"Decoded header: {decoded}")
            return decoded
        except Exception as e:
            logging.error(f"Error decoding header: {str(e)}")
            return header

    def parse_mailto(self, mailto_str):
         
        logging.info(f"Parsing mailto link: {mailto_str}")
        try:
 
            mailto_str = unquote(mailto_str.strip())
            if '?' in mailto_str:
                email_part, params_part = mailto_str.split('?', 1)
            else:
                email_part = mailto_str
                params_part = ''
                
 
            params = {}
            if params_part:
                param_pairs = params_part.split('&')
                for pair in param_pairs:
                    if '=' in pair:
                        key, value = pair.split('=', 1)
                        params[key.lower()] = unquote(value)
            
            result = {
                'email': email_part,
                'subject': params.get('subject', 'Unsubscribe'),
                'body': params.get('body', '')
            }
            logging.info(f"Parsed mailto info: {result}")
            return result
        except Exception as e:
            logging.error(f"Error parsing mailto: {str(e)}")
            return None

    def send_unsubscribe_email(self, mailto_info):
         
        logging.info(f"Preparing to send unsubscribe email to: {mailto_info['email']}")
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_address
            msg['To'] = mailto_info['email']
            msg['Subject'] = mailto_info['subject']
            
            body = mailto_info['body'] if mailto_info['body'] else 'Please unsubscribe me from this mailing list.'
            msg.attach(MIMEText(body, 'plain'))
            
            logging.info("Sending unsubscribe email...")
            self.smtp.send_message(msg, timeout=30)
            logging.info("Unsubscribe email sent successfully")
            return True
        except Exception as e:
            logging.error(f"Error sending unsubscribe email: {str(e)}")
            return False
    
    def clean_url(self, url):
         
        logging.info(f"Cleaning URL: {url}")
        try:
 
            url = url.replace('=3A//', '://')
            
 
            url = url.replace('=3A', ':')
            
 
            url = url.replace('=2E', '.')
            url = url.replace('=2F', '/')
            url = url.replace('=5F', '_')
            url = url.replace('=2D', '-')
            url = url.replace('=3D', '=')
            url = url.replace('=26', '&')
            url = url.replace('=3F', '?')
            
 
            url = unquote(url)
            
            logging.info(f"Cleaned URL: {url}")
            return url
        except Exception as e:
            logging.error(f"Error cleaning URL: {str(e)}")
            return url

    def extract_unsubscribe_info(self, header):
         
        logging.info("Extracting unsubscribe info from header")
        try:
 
            decoded_header = self.decode_header_string(header)
            
 
            urls = []
            mailtos = []
            
 
            parts = re.findall(r'<([^>]+)>', decoded_header)
            
            for part in parts:
                clean_part = self.clean_url(part).strip()
                if clean_part.startswith('http'):
                    urls.append(clean_part)
                elif clean_part.startswith('mailto:'):
                    mailtos.append(clean_part.replace('mailto:', ''))
            
            logging.info(f"Found URLs: {urls}")
            logging.info(f"Found mailto addresses: {mailtos}")
            
            return urls, mailtos
        except Exception as e:
            logging.error(f"Error extracting unsubscribe info: {str(e)}")
            return [], []

    def find_unsubscribe_info(self, domain, days_back=30):
         
        logging.info(f"Searching for unsubscribe info for domain: {domain}")
        if not self.mail:
            logging.error("No IMAP connection available")
            return None, None

        try:
            self.mail.select('inbox')
            date = (datetime.now() - timedelta(days=days_back)).strftime("%d-%b-%Y")
            logging.info(f"Searching emails since: {date}")
            
            _, messages = self.mail.search(None, f'(SINCE {date})')
            
            if not messages[0]:
                logging.info(f"No messages found for domain {domain}")
                return None, None
                
            email_ids = messages[0].split()
            logging.info(f"Found {len(email_ids)} emails to check")
            
            for email_id in reversed(email_ids):
                try:
                    logging.debug(f"Checking email ID: {email_id}")
                    _, msg_data = self.mail.fetch(email_id, '(RFC822)')
                    email_message = email.message_from_bytes(msg_data[0][1])
                    
                    from_header = email_message.get('from', '')
                    if domain.lower() in from_header.lower():
                        logging.info(f"Found matching email from: {from_header}")
                        unsubscribe_header = email_message.get('List-Unsubscribe')
                        if unsubscribe_header:
                            logging.info(f"Found List-Unsubscribe header: {unsubscribe_header}")
                            return self.extract_unsubscribe_info(unsubscribe_header)
                except Exception as e:
                    logging.error(f"Error processing email {email_id}: {str(e)}")
                    continue
                    
        except Exception as e:
            logging.error(f"Error searching emails for {domain}: {str(e)}")
            
        logging.info(f"No unsubscribe information found for {domain}")
        return None, None

    def unsubscribe_from_domain(self, domain):
         
        logging.info(f"\n{'='*50}\nProcessing unsubscribe request for {domain}")
        
        urls, mailtos = self.find_unsubscribe_info(domain)
        success = False
        
        if urls:
 
            for url in urls:
                logging.info(f"Attempting HTTP unsubscribe: {url}")
                try:
                    response = requests.get(url, timeout=30)
                    if response.status_code == 200:
                        logging.info(f"Successfully unsubscribed from {domain} via HTTP")
                        success = True
                        break
                    else:
                        logging.warning(f"HTTP unsubscribe failed for {domain} (Status: {response.status_code})")
                except Exception as e:
                    logging.error(f"Error during HTTP unsubscribe for {domain}: {str(e)}")
        
        if not success and mailtos:
            logging.info("HTTP unsubscribe failed or unavailable, trying mailto")
            for mailto in mailtos:
                mailto_info = self.parse_mailto(mailto)
                if mailto_info and self.send_unsubscribe_email(mailto_info):
                    logging.info(f"Successfully sent unsubscribe email to {mailto_info['email']}")
                    success = True
                    break
                else:
                    logging.error(f"Failed to send unsubscribe email for {domain}")
        
        if not success:
            logging.warning(f"No successful unsubscribe method found for {domain}")
        
        return success

    def process_csv(self, csv_path):
         
        logging.info(f"Processing CSV file: {csv_path}")
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                total_rows = sum(1 for row in reader)
                f.seek(0)  # Reset file pointer
                next(reader)  # Skip header row
                
                for i, row in enumerate(reader, 1):
                    logging.info(f"Processing row {i} of {total_rows}")
                    if (row['Delete'].strip().lower() == 'yes' and 
                        row['List-Unsubscribe'].strip().lower() == 'yes' and 
                        row['Domain'] not in self.processed_domains):
                        
                        if self.unsubscribe_from_domain(row['Domain']):
                            self.processed_domains.add(row['Domain'])
        except Exception as e:
            logging.error(f"Error processing CSV: {str(e)}")

    def close(self):
         
        logging.info("Closing connections")
        if self.mail:
            try:
                self.mail.close()
                self.mail.logout()
                logging.info("IMAP connection closed")
            except:
                logging.error("Error closing IMAP connection")
        
        if self.smtp:
            try:
                self.smtp.quit()
                logging.info("SMTP connection closed")
            except:
                logging.error("Error closing SMTP connection")


def main():
    parser = argparse.ArgumentParser(description='Email Unsubscribe Automation')
    parser.add_argument('-e', '--email', required=True, help='Email address')
    parser.add_argument('-p', '--password', required=True, help='Email password or app password')
    parser.add_argument('-c', '--csv', required=True, help='Path to domain analysis CSV file')
    parser.add_argument('-s', '--server', default='imap.gmail.com', help='IMAP server (default: imap.gmail.com)')
    parser.add_argument('-d', '--days', type=int, default=30, help='Number of days back to search (default: 30)')
    
    args = parser.parse_args()
    
    automation = UnsubscribeAutomation(args.email, args.password, args.server)
    
    if automation.connect():
        automation.process_csv(args.csv)
        automation.close()
        
        if automation.processed_domains:
            logging.info("\nProcessed domains:")
            for domain in sorted(automation.processed_domains):
                logging.info(f"- {domain}")
        logging.info("Unsubscribe process completed!")
    else:
        logging.error("Failed to connect to email servers")


if __name__ == "__main__":
    main()