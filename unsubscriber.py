import imaplib
import email
import csv
import argparse
import re
import requests
import smtplib
import logging
import sys
import shutil
import tempfile
from pathlib import Path
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
        logging.basicConfig(level=logging.ERROR, format='%(levelname)s - %(message)s')

    def connect(self):
        """Connect to both IMAP and SMTP servers"""
        try:
            self.mail = imaplib.IMAP4_SSL(self.imap_server)
            self.mail.login(self.email_address, self.password)
            
            self.smtp = smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=30)
            self.smtp.starttls()
            self.smtp.login(self.email_address, self.password)
            
            return True
        except Exception as e:
            logging.error(f"Connection error: {str(e)}")
            return False

    def parse_mailto(self, mailto_str):
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
            
            return {
                'email': email_part,
                'subject': params.get('subject', 'Unsubscribe'),
                'body': params.get('body', '')
            }
        except Exception as e:
            logging.error(f"Error parsing mailto: {str(e)}")
            return None

    def send_unsubscribe_email(self, mailto_info):
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_address
            msg['To'] = mailto_info['email']
            msg['Subject'] = mailto_info['subject']
            
            body = mailto_info['body'] if mailto_info['body'] else 'Please unsubscribe me from this mailing list.'
            msg.attach(MIMEText(body, 'plain'))
            
            self.smtp.send_message(msg, timeout=30)
            return True
        except Exception as e:
            logging.error(f"Error sending unsubscribe email: {str(e)}")
            return False

    def extract_unsubscribe_info_from_header(self, header):
        urls = re.findall(r'<(https?://[^>]+)>', header)
        mailtos = re.findall(r'<mailto:([^>]+)>', header)
        return urls, mailtos

    def clean_url(self, url):
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
            return url
        except Exception as e:
            logging.error(f"Error cleaning URL: {str(e)}")
            return url

    def try_unsubscribe_with_stored_data(self, row):
        """Attempt to unsubscribe using stored information from CSV"""
        domain = row['Domain']
        success = False
        error_reason = None
        
        # Try stored HTTP URLs first
        if row.get('Unsubscribe URLs'):
            urls = [url.strip() for url in row['Unsubscribe URLs'].split(';') if url.strip()]
            for url in urls:
                try:
                    response = requests.get(url, timeout=30)
                    if response.status_code == 200:
                        return True, "Success via stored HTTP URL"
                    else:
                        error_reason = f"HTTP {response.status_code}"
                except Exception as e:
                    error_reason = f"HTTP request failed: {str(e)}"

        # Try stored mailto addresses
        if not success and row.get('Unsubscribe Mailtos'):
            mailtos = [mailto.strip() for mailto in row['Unsubscribe Mailtos'].split(';') if mailto.strip()]
            for mailto in mailtos:
                mailto_info = self.parse_mailto(mailto)
                if mailto_info and self.send_unsubscribe_email(mailto_info):
                    return True, "Success via stored mailto"
                else:
                    error_reason = error_reason or "Mailto failed"

        # Try original unsubscribe header if available
        if not success and row.get('Unsubscribe Header'):
            try:
                urls = re.findall(r'<(https?://[^>]+)>', row['Unsubscribe Header'])
                mailtos = re.findall(r'<mailto:([^>]+)>', row['Unsubscribe Header'])
                
                for url in urls:
                    try:
                        response = requests.get(url, timeout=30)
                        if response.status_code == 200:
                            return True, "Success via header URL"
                        else:
                            error_reason = f"Header HTTP {response.status_code}"
                    except Exception as e:
                        error_reason = error_reason or f"Header HTTP failed: {str(e)}"
                
                for mailto in mailtos:
                    mailto_info = self.parse_mailto(mailto)
                    if mailto_info and self.send_unsubscribe_email(mailto_info):
                        return True, "Success via header mailto"
                    else:
                        error_reason = error_reason or "Header mailto failed"
                        
            except Exception as e:
                error_reason = error_reason or f"Header processing failed: {str(e)}"
        
        return False, error_reason or "All methods failed"

    def process_csv(self, csv_path):
        """Process the domain analysis CSV file and update with results"""
        try:
            # Create a temporary file for writing
            temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, newline='')
            
            with open(csv_path, 'r', newline='') as csvfile:
                reader = csv.DictReader(csvfile)
                fieldnames = ['Status'] + reader.fieldnames  # Add Status column
                
                writer = csv.DictWriter(temp_file, fieldnames=fieldnames)
                writer.writeheader()
                
                total_rows = sum(1 for _ in reader)
                csvfile.seek(0)
                next(reader)  # Skip header again
                
                for i, row in enumerate(reader, 1):
                    print(f"\rProcessing {i}/{total_rows}", end='', flush=True)
                    
                    if (row['Delete'].strip().lower() == 'yes' and 
                        row['List-Unsubscribe'].strip().lower() == 'yes' and 
                        row['Domain'] not in self.processed_domains):
                        
                        success, status_message = self.try_unsubscribe_with_stored_data(row)
                        if success:
                            self.processed_domains.add(row['Domain'])
                        row['Status'] = status_message
                    else:
                        row['Status'] = 'Skipped'
                    
                    writer.writerow(row)
            
            print("\n")  # New line after progress
            temp_file.close()
            
            # Replace the original file with the updated one
            shutil.move(temp_file.name, csv_path)
            
        except Exception as e:
            logging.error(f"Error processing CSV: {str(e)}")
            if temp_file:
                Path(temp_file.name).unlink(missing_ok=True)

    def close(self):
        """Close all connections"""
        if self.mail:
            try:
                self.mail.close()
                self.mail.logout()
            except:
                pass
        
        if self.smtp:
            try:
                self.smtp.quit()
            except:
                pass


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
        print("Processing unsubscribe requests...")
        automation.process_csv(args.csv)
        automation.close()
        
        if automation.processed_domains:
            print(f"\nSuccessfully processed {len(automation.processed_domains)} domains")
            print("\nSuccessfully unsubscribed from:")
            for domain in sorted(automation.processed_domains):
                print(f"- {domain}")
        print("\nDone! Check the CSV file for detailed results.")
        print("Remember to delete your temporary Gmail app password if you used one!")
    else:
        print("Failed to connect to email servers")


if __name__ == "__main__":
    main()