# Events2Go Email Templates

This directory contains professional, enterprise-level email templates for the Events2Go application. All templates are designed with modern styling, responsive design, and accessibility in mind.

## Available Templates

### 1. Email Verification (`email_verification.html`)
**Purpose**: Welcome new users and verify their email address
**Usage**: `send_email_verification()`
**Variables**:
- `username` - User's display name
- `verification_link` - Email verification URL
- `logo_url` - Company logo URL (optional)
- `year` - Current year

### 2. Phone OTP (`phone_otp.html`)
**Purpose**: Send phone number verification codes
**Usage**: `send_phone_otp_email()`
**Variables**:
- `username` - User's display name
- `phone_number` - Phone number being verified
- `otp_code` - 6-digit verification code
- `expiry_minutes` - Code expiration time (default: 10)
- `logo_url` - Company logo URL (optional)
- `year` - Current year

### 3. Password Reset (`password_reset.html`)
**Purpose**: Secure password reset with detailed activity information
**Usage**: `send_password_reset_email()`
**Variables**:
- `username` - User's display name
- `email` - User's email address
- `reset_link` - Password reset URL
- `ip_address` - Request IP address (optional)
- `request_time` - When the request was made
- `expiry_hours` - Link expiration time (default: 24)
- `logo_url` - Company logo URL (optional)
- `year` - Current year

### 4. Account Activated (`account_activated.html`)
**Purpose**: Celebrate successful account activation
**Usage**: `send_account_activated_email()`
**Variables**:
- `username` - User's display name
- `email` - User's email address
- `account_type` - Type of account (default: "Standard")
- `activation_date` - When account was activated
- `dashboard_url` - Link to user dashboard
- `profile_url` - Link to user profile
- `logo_url` - Company logo URL (optional)
- `year` - Current year

### 5. Security Alert (`security_alert.html`)
**Purpose**: Notify users of suspicious account activity
**Usage**: `send_security_alert_email()`
**Variables**:
- `username` - User's display name
- `alert_type` - Type of security alert
- `activity_time` - When the activity occurred
- `ip_address` - Source IP address (optional)
- `location` - Geographic location (optional)
- `device_info` - Device information (optional)
- `secure_account_url` - Link to security settings
- `review_activity_url` - Link to activity log
- `logo_url` - Company logo URL (optional)
- `year` - Current year

### 6. Booking Confirmation (`booking_confirmation.html`)
**Purpose**: Confirm event ticket bookings with detailed information
**Usage**: `send_booking_confirmation_email()`
**Variables**:
- `username` - User's display name
- `customer_email` - Customer's email address
- `booking_id` - Unique booking reference
- `event_title` - Name of the event
- `event_date` - Event date
- `event_time` - Event time
- `venue_name` - Venue name
- `ticket_quantity` - Number of tickets
- `ticket_type` - Type of tickets
- `ticket_price` - Price per ticket
- `total_amount` - Total amount paid
- `service_fee` - Service fee (optional)
- `taxes` - Tax amount (optional)
- `event_image` - Event image URL (optional)
- `qr_code_url` - QR code image URL (optional)
- `ticket_url` - Link to digital ticket
- `calendar_url` - Add to calendar link (optional)
- `logo_url` - Company logo URL (optional)
- `year` - Current year

### 7. Welcome Email (`welcome_email.html`)
**Purpose**: Welcome admin users with login credentials
**Usage**: `send_welcome_email()`
**Variables**:
- `username` - Admin user's display name
- `email` - Admin user's email address
- `password` - Temporary password
- `welcome_url` - Link to admin dashboard
- `logo_url` - Company logo URL (optional)
- `year` - Current year

## Design Features

### 🎨 Modern Design
- Clean, professional layout
- Gradient backgrounds and modern color schemes
- Consistent branding throughout all templates
- Eye-catching icons and visual elements

### 📱 Responsive Design
- Mobile-first approach
- Optimized for all screen sizes
- Touch-friendly buttons and links
- Readable typography on all devices

### ♿ Accessibility
- High contrast colors for readability
- Semantic HTML structure
- Alt text for images
- Screen reader friendly

### 🌙 Dark Mode Support
- Automatic dark mode detection
- Optimized colors for dark themes
- Maintains readability in all modes

### 📧 Email Client Compatibility
- Tested across major email clients
- Fallback styles for older clients
- MSO (Microsoft Outlook) specific optimizations
- Progressive enhancement approach

## Technical Specifications

### CSS Framework
- Inline CSS for maximum compatibility
- CSS Grid and Flexbox with fallbacks
- Custom animations and transitions
- Media queries for responsive design

### Template Engine
- Jinja2 template syntax
- Conditional rendering with `{% if %}` blocks
- Variable substitution with `{{ variable }}`
- Default values with `{{ variable | default('fallback') }}`

### Color Palette
- Primary: `#667eea` to `#764ba2` (gradient)
- Success: `#48bb78` to `#38a169` (gradient)
- Warning: `#f6ad55` to `#ed8936` (gradient)
- Error: `#e53e3e` to `#c53030` (gradient)
- Neutral: `#2d3748`, `#4a5568`, `#718096`, `#a0aec0`

### Typography
- Font Stack: `-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif`
- Headings: 700 weight, various sizes
- Body: 400 weight, 16px base size
- Code: `'Courier New', monospace`

## Usage Examples

```python
from utils.email import (
    send_email_verification,
    send_phone_otp_email,
    send_password_reset_email,
    send_account_activated_email,
    send_security_alert_email,
    send_booking_confirmation_email,
    send_welcome_email
)

# Email verification
send_email_verification(
    email="user@example.com",
    username="John Doe",
    verification_link="https://events2go.com/verify/abc123",
    logo_url="https://events2go.com/logo.png"
)

# Phone OTP
send_phone_otp_email(
    email="user@example.com",
    username="John Doe",
    phone_number="+1 (555) 123-4567",
    otp_code="123456",
    expiry_minutes=10
)

# Password reset
send_password_reset_email(
    email="user@example.com",
    username="John Doe",
    reset_link="https://events2go.com/reset/xyz789",
    ip_address="192.168.1.1",
    request_time="2024-01-15 14:30:00 UTC"
)

# Booking confirmation
send_booking_confirmation_email(
    email="user@example.com",
    username="John Doe",
    booking_id="EVT-2024-001",
    event_title="Summer Music Festival",
    event_date="July 15, 2024",
    event_time="7:00 PM",
    venue_name="Central Park",
    ticket_quantity=2,
    ticket_type="General Admission",
    ticket_price="$75.00",
    total_amount="$150.00"
)
```

## Customization

### Adding New Templates
1. Create a new HTML file in the `templates/` directory
2. Follow the existing design patterns and structure
3. Add the corresponding function in `utils/email.py`
4. Update this documentation

### Modifying Existing Templates
1. Edit the HTML template file
2. Test across different email clients
3. Update the function parameters if needed
4. Update documentation

### Brand Customization
- Update color variables in the CSS
- Replace logo URLs with your brand assets
- Modify typography to match brand guidelines
- Adjust spacing and layout as needed

## Testing

### Email Client Testing
- Gmail (Web, Mobile)
- Outlook (Desktop, Web, Mobile)
- Apple Mail (Desktop, Mobile)
- Yahoo Mail
- Thunderbird

### Device Testing
- Desktop (1920x1080, 1366x768)
- Tablet (768x1024, 1024x768)
- Mobile (375x667, 414x896, 360x640)

### Accessibility Testing
- Screen reader compatibility
- Keyboard navigation
- Color contrast ratios
- Text scaling support

## Best Practices

### Content
- Keep subject lines under 50 characters
- Use clear, action-oriented language
- Include all necessary information
- Provide alternative contact methods

### Design
- Maintain consistent branding
- Use white space effectively
- Ensure buttons are touch-friendly (44px minimum)
- Test with images disabled

### Security
- Never include sensitive data in templates
- Use HTTPS for all links
- Implement proper token expiration
- Include security warnings where appropriate

### Performance
- Optimize images for email
- Keep HTML size under 100KB
- Use efficient CSS selectors
- Minimize external dependencies

## Support

For questions or issues with email templates:
- Check the logs in `utils/email.py`
- Test templates in email client preview tools
- Validate HTML structure
- Contact the development team

---

*Last updated: January 2024*
*Version: 2.0*
