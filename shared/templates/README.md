# Events2Go Email Templates

This directory contains professional, enterprise-level email templates for the Events2Go application. All templates are designed with modern styling, responsive design, and accessibility in mind.

## Template Structure

### User Templates (`user/`)
Templates for end-user communications including registration, bookings, notifications, and account management.

### Admin Templates (`admin/`)
Templates for administrative communications including event management, user management, and system notifications.

## Available Templates

### User Templates

#### 1. Welcome User (`user/welcome_user.html`)
**Purpose**: Welcome new users with account details
**Usage**: `send_welcome_email()`
**Variables**:
- `username` - User's display name
- `email` - User's email address
- `password` - Initial password
- `welcome_url` - Link to application
- `logo_url` - Company logo URL (optional)
- `year` - Current year

#### 2. Email Verification (`user/email_verification.html`)
**Purpose**: Welcome new users and verify their email address
**Usage**: `send_user_verification_email()`
**Variables**:
- `username` - User's display name
- `email` - User's email address
- `verification_link` - Email verification URL
- `welcome_url` - Link to application
- `year` - Current year

#### 3. Phone OTP (`user/phone_otp.html`)
**Purpose**: Send phone number verification codes
**Usage**: `send_phone_otp_email()`
**Variables**:
- `username` - User's display name
- `phone_number` - Phone number being verified
- `otp_code` - 6-digit verification code
- `expiry_minutes` - Code expiration time (default: 10)
- `year` - Current year

#### 4. Password Reset (`user/password_reset.html`)
**Purpose**: Secure password reset with detailed activity information
**Usage**: `send_password_reset_email()`
**Variables**:
- `username` - User's display name
- `email` - User's email address
- `reset_link` - Password reset URL
- `ip_address` - Request IP address (optional)
- `request_time` - When the request was made
- `expiry_hours` - Link expiration time (default: 24)
- `year` - Current year

#### 5. Account Activated (`user/account_activated.html`)
**Purpose**: Celebrate successful account activation
**Usage**: `send_account_activated_email()`
**Variables**:
- `username` - User's display name
- `email` - User's email address
- `account_type` - Type of account (default: "Standard")
- `activation_date` - When account was activated
- `dashboard_url` - Link to user dashboard
- `profile_url` - Link to user profile
- `year` - Current year

#### 6. Account Locked (`user/account_locked.html`)
**Purpose**: Notify users when their account is locked
**Usage**: `send_account_locked_email()`
**Variables**:
- `username` - User's display name
- `lock_reason` - Reason for account lock
- `unlock_url` - Link to unlock account
- `support_url` - Link to support
- `year` - Current year

#### 7. Account Unlock (`user/account_unlock.html`)
**Purpose**: Provide account unlock instructions
**Usage**: `send_account_unlock_email()`
**Variables**:
- `username` - User's display name
- `unlock_link` - Account unlock URL with token
- `expiry_hours` - Link expiration time (default: 24)
- `year` - Current year

#### 8. Security Alert (`user/security_alert.html`)
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
- `year` - Current year

#### 9. Booking Confirmation (`user/booking_confirmation.html`)
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
- `year` - Current year

#### 10. Event Reminder (`user/event_reminder.html`)
**Purpose**: Remind users about upcoming events
**Usage**: `send_event_reminder_email()`
**Variables**:
- `username` - User's display name
- `event_title` - Name of the event
- `event_date` - Event date
- `event_time` - Event time
- `venue_name` - Venue name
- `venue_address` - Venue address (optional)
- `booking_id` - Booking reference (optional)
- `ticket_type` - Type of tickets (optional)
- `ticket_quantity` - Number of tickets (optional)
- `days_remaining` - Days until event (optional)
- `hours_remaining` - Hours until event (optional)
- `minutes_remaining` - Minutes until event (optional)
- `event_image` - Event image URL (optional)
- `ticket_url` - Link to tickets (optional)
- `calendar_url` - Add to calendar link (optional)
- `event_url` - Event details link (optional)
- `additional_notes` - Extra information (optional)
- `year` - Current year

#### 11. Event Canceled (`user/event_canceled.html`)
**Purpose**: Notify users about event cancellations
**Usage**: `send_event_canceled_email()`
**Variables**:
- `username` - User's display name
- `event_title` - Name of the event
- `event_date` - Original event date
- `event_time` - Original event time
- `venue_name` - Venue name
- `booking_id` - Booking reference (optional)
- `cancellation_reason` - Reason for cancellation (optional)
- `refund_amount` - Refund amount (optional)
- `refund_processing_time` - Refund timeline (optional)
- `refund_method` - Refund method (optional)
- `dashboard_url` - Link to dashboard
- `support_url` - Link to support
- `year` - Current year

#### 12. Payment Confirmation (`user/payment_confirmation.html`)
**Purpose**: Confirm successful payments
**Usage**: `send_payment_confirmation_email()`
**Variables**:
- `username` - User's display name
- `transaction_id` - Payment transaction ID
- `total_amount` - Total amount paid
- `payment_method` - Payment method used (optional)
- `payment_date` - Payment date (optional)
- `event_title` - Event name (optional)
- `event_date` - Event date (optional)
- `event_time` - Event time (optional)
- `venue_name` - Venue name (optional)
- `venue_address` - Venue address (optional)
- `booking_id` - Booking reference (optional)
- `ticket_quantity` - Number of tickets (optional)
- `ticket_type` - Type of tickets (optional)
- `ticket_price` - Price per ticket (optional)
- `ticket_subtotal` - Subtotal (optional)
- `service_fee` - Service fee (optional)
- `taxes` - Tax amount (optional)
- `discount_amount` - Discount applied (optional)
- `ticket_url` - Link to tickets (optional)
- `dashboard_url` - Link to dashboard
- `receipt_url` - Link to receipt (optional)
- `additional_instructions` - Extra information (optional)
- `year` - Current year

#### 13. Newsletter Subscription (`user/newsletter_subscription.html`)
**Purpose**: Confirm newsletter subscription
**Usage**: `send_newsletter_subscription_email()`
**Variables**:
- `username` - User's display name (optional)
- `email` - User's email address
- `subscription_date` - Subscription date (optional)
- `frequency` - Newsletter frequency (optional)
- `interests` - User interests (optional)
- `browse_events_url` - Link to browse events
- `preferences_url` - Link to preferences
- `account_settings_url` - Link to account settings
- `incentive_offer` - Special offer (optional)
- `year` - Current year

#### 14. Feedback Request (`user/feedback_request.html`)
**Purpose**: Request feedback after event attendance
**Usage**: `send_feedback_request_email()`
**Variables**:
- `username` - User's display name
- `event_title` - Name of the event
- `event_date` - Event date
- `venue_name` - Venue name
- `feedback_url` - Link to feedback form
- `booking_id` - Booking reference (optional)
- `attendance_date` - Attendance date (optional)
- `detailed_feedback_url` - Link to detailed feedback (optional)
- `incentive_offer` - Feedback incentive (optional)
- `facebook_share_url` - Facebook share link (optional)
- `twitter_share_url` - Twitter share link (optional)
- `linkedin_share_url` - LinkedIn share link (optional)
- `year` - Current year

#### 15. Ticket Delivery (`user/ticket_delivery.html`)
**Purpose**: Deliver digital tickets to users
**Usage**: `send_ticket_delivery_email()`
**Variables**:
- `username` - User's display name
- `event_title` - Name of the event
- `event_date` - Event date
- `event_time` - Event time
- `venue_name` - Venue name
- `booking_id` - Booking reference
- `ticket_quantity` - Number of tickets
- `ticket_type` - Type of tickets (optional)
- `qr_code_url` - QR code image URL (optional)
- `download_url` - Ticket download link (optional)
- `calendar_url` - Add to calendar link (optional)
- `event_url` - Event details link (optional)
- `additional_instructions` - Entry instructions (optional)
- `year` - Current year

#### 16. Event Update (`user/event_update.html`)
**Purpose**: Notify users about event changes
**Usage**: `send_event_update_email()`
**Variables**:
- `username` - User's display name
- `event_title` - Name of the event
- `event_date` - Event date
- `event_time` - Event time
- `venue_name` - Venue name
- `update_type` - Type of update (default: "information")
- `booking_id` - Booking reference (optional)
- `changes` - List of changes (optional)
- `action_required` - Required action text (optional)
- `important_notice` - Important notice text (optional)
- `event_url` - Event details link (optional)
- `ticket_url` - Link to tickets (optional)
- `calendar_url` - Update calendar link (optional)
- `requires_confirmation` - Whether confirmation is needed (default: false)
- `confirmation_url` - Confirmation link (optional)
- `year` - Current year

### Admin Templates

#### 1. Admin Welcome (`admin/welcome_admin.html`)
**Purpose**: Welcome new admin users with credentials
**Usage**: `send_admin_welcome_email()`
**Variables**:
- `username` - Admin user's display name
- `email` - Admin user's email address
- `password` - Initial password
- `role` - Admin role (default: "Administrator")
- `welcome_url` - Link to admin dashboard
- `year` - Current year

#### 2. Admin Password Reset (`admin/password_reset.html`)
**Purpose**: Admin password reset functionality
**Usage**: `send_admin_password_reset_email()`
**Variables**:
- `username` - Admin user's display name
- `email` - Admin user's email address
- `reset_link` - Password reset URL
- `ip_address` - Request IP address (optional)
- `request_time` - When the request was made (optional)
- `expiry_hours` - Link expiration time (default: 24)
- `year` - Current year

#### 3. New Event Submission (`admin/new_event_submission.html`)
**Purpose**: Notify admins about new event submissions
**Usage**: `send_admin_new_event_notification()`
**Variables**:
- `admin_name` - Admin user's display name
- `event_id` - Event ID
- `event_title` - Name of the event
- `event_date` - Event date
- `event_time` - Event time
- `venue_name` - Venue name
- `event_category` - Event category (optional)
- `event_capacity` - Event capacity (optional)
- `ticket_price` - Ticket price (optional)
- `submission_date` - Submission date (optional)
- `organizer_name` - Organizer name
- `organizer_email` - Organizer email
- `organizer_phone` - Organizer phone (optional)
- `organizer_id` - Organizer ID
- `organizer_events_count` - Number of organizer's events (optional)
- `priority` - Priority level (default: "medium")
- `pending_events_count` - Number of pending events (optional)
- `total_events_today` - Events submitted today (optional)
- `approved_events_count` - Approved events count (optional)
- `rejected_events_count` - Rejected events count (optional)
- `approve_url` - Quick approve link
- `reject_url` - Quick reject link
- `review_url` - Review event link
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
