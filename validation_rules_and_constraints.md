# Django Tutoring Platform - Validation Rules and Constraints

## 1. Overview

This document outlines all validation rules and constraints for the Django tutoring platform database models. These rules ensure data integrity, business logic compliance, and system security.

## 2. Accounts App Validation Rules

### 2.1 User Model

#### Field Validations
- **username**: 
  - Required, unique, max 150 characters
  - Alphanumeric characters, underscores, hyphens only
  - Cannot start or end with underscore or hyphen
  - Case-insensitive unique check

- **email**:
  - Required, unique, valid email format
  - Case-insensitive unique check
  - Must be verified before certain actions

- **first_name**, **last_name**:
  - Max 30 characters each
  - Alphabetic characters with spaces, hyphens, apostrophes allowed

- **user_type**:
  - Must be one of: 'STUDENT', 'TUTOR', 'ADMIN'
  - Cannot be changed after account creation without admin approval

- **phone_number**:
  - Optional, must be valid international format if provided
  - Must include country code

- **timezone**:
  - Must be valid IANA timezone identifier
  - Default: 'UTC'

#### Model Constraints
- Email and username must be unique (case-insensitive)
- User type cannot be empty
- Staff status requires admin approval

#### Custom Validation Methods
```python
def clean(self):
    # Validate phone number format
    if self.phone_number and not re.match(r'^\+\d{10,15}$', self.phone_number):
        raise ValidationError("Invalid phone number format")
    
    # Validate timezone
    try:
        pytz.timezone(self.timezone)
    except pytz.UnknownTimeZoneError:
        raise ValidationError("Invalid timezone")
```

### 2.2 StudentProfile Model

#### Field Validations
- **educational_status**: Must be one of: 'K12', 'UNDERGRADUATE', 'GRADUATE', 'PROFESSIONAL'
- **institution**: Max 200 characters, alphanumeric with spaces
- **grade_level**: Valid based on educational_status
- **major_field**: Max 100 characters, valid academic field
- **preferred_learning_style**: Must be one of: 'VISUAL', 'AUDITORY', 'KINESTHETIC', 'READING'

#### Model Constraints
- One StudentProfile per User (OneToOne relationship)
- Grade level must match educational status range

#### Custom Validation Methods
```python
def clean(self):
    # Validate grade level based on educational status
    if self.educational_status == 'K12' and self.grade_level:
        if not self.grade_level.isdigit() or int(self.grade_level) > 12:
            raise ValidationError("Invalid grade level for K-12 education")
```

### 2.3 TutorProfile Model

#### Field Validations
- **experience_years**: Non-negative integer, max 50
- **hourly_rate_min**: Non-negative, max 9999.99
- **hourly_rate_max**: Non-negative, max 9999.99
- **response_time_hours**: Positive integer, max 168 (1 week)
- **profile_completion_score**: 0-100 inclusive

#### Model Constraints
- hourly_rate_max must be >= hourly_rate_min if both provided
- One TutorProfile per User (OneToOne relationship)
- Experience years must be reasonable (0-50)

#### Custom Validation Methods
```python
def clean(self):
    if self.hourly_rate_min and self.hourly_rate_max:
        if self.hourly_rate_max < self.hourly_rate_min:
            raise ValidationError("Maximum rate must be greater than or equal to minimum rate")
    
    if self.experience_years < 0:
        raise ValidationError("Experience years cannot be negative")
    
    if self.experience_years > 50:
        raise ValidationError("Experience years cannot exceed 50")
```

### 2.4 Subject Model

#### Field Validations
- **name**: Required, unique, max 100 characters
- **slug**: Required, unique, max 100 characters, URL-safe
- **order**: Non-negative integer

#### Model Constraints
- Name must be unique (case-insensitive)
- Slug must be unique (case-insensitive)
- Parent cannot be self (prevent circular references)
- Maximum hierarchy depth: 5 levels

#### Custom Validation Methods
```python
def clean(self):
    if self.parent and self.parent.id == self.id:
        raise ValidationError("A subject cannot be its own parent")
    
    # Check for circular references
    if self.parent:
        parent = self.parent
        while parent:
            if parent.id == self.id:
                raise ValidationError("Circular reference detected in subject hierarchy")
            parent = parent.parent
```

### 2.5 TutorSubject Model

#### Field Validations
- **proficiency_level**: Must be one of: 'BEGINNER', 'INTERMEDIATE', 'ADVANCED', 'EXPERT'
- **hourly_rate**: Non-negative, max 9999.99
- **years_of_experience**: Non-negative integer, max 50

#### Model Constraints
- Unique constraint on (tutor, subject)
- Years of experience cannot exceed tutor's total experience

#### Custom Validation Methods
```python
def clean(self):
    if self.years_of_experience and self.tutor.experience_years:
        if self.years_of_experience > self.tutor.experience_years:
            raise ValidationError("Subject experience cannot exceed total experience")
```

## 3. Requirements App Validation Rules

### 3.1 Requirement Model

#### Field Validations
- **title**: Required, max 200 characters
- **slug**: Required, unique, max 200 characters, URL-safe
- **description**: Required, min 50 characters, max 5000
- **learning_level**: Must be one of: 'ELEMENTARY', 'MIDDLE_SCHOOL', 'HIGH_SCHOOL', 'UNDERGRADUATE', 'GRADUATE', 'PROFESSIONAL'
- **budget_min**: Non-negative, max 999999.99
- **budget_max**: Non-negative, max 999999.99
- **session_duration**: Positive integer, max 480 (8 hours)
- **number_of_sessions**: Positive integer, max 100
- **deadline**: Must be future date if provided
- **urgency_level**: Must be one of: 'LOW', 'MEDIUM', 'HIGH', 'URGENT'

#### Model Constraints
- budget_max must be >= budget_min if both provided
- Deadline must be at least 24 hours in future
- Status transitions must follow business rules
- Only students can post requirements

#### Custom Validation Methods
```python
def clean(self):
    if self.budget_min and self.budget_max:
        if self.budget_max < self.budget_min:
            raise ValidationError("Maximum budget must be greater than or equal to minimum budget")
    
    if self.deadline and self.deadline <= timezone.now() + timedelta(hours=24):
        raise ValidationError("Deadline must be at least 24 hours in the future")
    
    if self.session_duration and (self.session_duration < 15 or self.session_duration > 480):
        raise ValidationError("Session duration must be between 15 minutes and 8 hours")
    
    if self.number_of_sessions and self.number_of_sessions < 1:
        raise ValidationError("Number of sessions must be at least 1")
```

### 3.2 Proposal Model

#### Field Validations
- **cover_letter**: Required, min 100 characters, max 5000
- **proposed_rate**: Positive, max 9999.99
- **estimated_hours**: Positive integer, max 1000
- **total_amount**: Positive, max 99999.99

#### Model Constraints
- Total amount must equal rate × hours if both provided
- Tutor cannot submit proposal to own requirement
- Only one proposal per tutor per requirement
- Proposal must be submitted before requirement deadline

#### Custom Validation Methods
```python
def clean(self):
    if self.tutor.id == self.requirement.student.id:
        raise ValidationError("Cannot submit proposal to own requirement")
    
    if self.requirement.deadline and self.requirement.deadline <= timezone.now():
        raise ValidationError("Cannot submit proposal to expired requirement")
    
    if self.estimated_hours and self.proposed_rate:
        calculated_total = self.estimated_hours * self.proposed_rate
        if self.total_amount and abs(calculated_total - self.total_amount) > 0.01:
            raise ValidationError("Total amount must equal rate multiplied by hours")
```

### 3.3 Award Model

#### Field Validations
- **agreed_rate**: Positive, max 9999.99
- **total_amount**: Positive, max 99999.99
- **start_date**: Must be future date
- **expected_end_date**: Must be after start_date

#### Model Constraints
- Only accepted proposals can become awards
- Start date must be after award creation
- Expected end date must be after start date
- Total amount must match agreed rate × estimated hours

#### Custom Validation Methods
```python
def clean(self):
    if self.start_date and self.start_date <= timezone.now().date():
        raise ValidationError("Start date must be in the future")
    
    if self.expected_end_date and self.start_date:
        if self.expected_end_date <= self.start_date:
            raise ValidationError("Expected end date must be after start date")
```

## 4. Messaging App Validation Rules

### 4.1 MaskedEmail Model

#### Field Validations
- **masked_address**: Required, unique, valid email format
- **student_real_email**: Required, valid email format
- **tutor_real_email**: Required, valid email format
- **expires_at**: Must be future date

#### Model Constraints
- Masked email must be unique
- Expiration must be at least 7 days in future
- Only one masked email per award
- Student and tutor must be award participants

#### Custom Validation Methods
```python
def clean(self):
    if self.expires_at and self.expires_at <= timezone.now():
        raise ValidationError("Expiration date must be in the future")
    
    if self.expires_at and self.expires_at <= timezone.now() + timedelta(days=7):
        raise ValidationError("Expiration date must be at least 7 days in the future")
```

### 4.2 Conversation Model

#### Field Validations
- **subject**: Max 200 characters if provided

#### Model Constraints
- Participant1 and participant2 must be different users
- Only one conversation per pair of users per award/proposal
- Cannot delete conversation if there are unread messages

#### Custom Validation Methods
```python
def clean(self):
    if self.participant1_id == self.participant2_id:
        raise ValidationError("Participants must be different users")
```

### 4.3 Message Model

#### Field Validations
- **content**: Required, max 10000 characters
- **message_type**: Must be one of: 'TEXT', 'FILE', 'SYSTEM', 'NOTIFICATION'

#### Model Constraints
- Sender must be conversation participant
- Content cannot be empty for text messages
- Parent message must belong to same conversation

#### Custom Validation Methods
```python
def clean(self):
    if self.message_type == 'TEXT' and not self.content.strip():
        raise ValidationError("Text messages cannot be empty")
    
    if self.parent_message and self.parent_message.conversation_id != self.conversation_id:
        raise ValidationError("Parent message must belong to same conversation")
```

## 5. Payments App Validation Rules

### 5.1 PaymentMethod Model

#### Field Validations
- **card_exp_month**: 1-12 if provided
- **card_exp_year**: Current year + 10 years max
- **card_last4**: Exactly 4 digits if provided
- **paypal_email**: Valid email format if provided

#### Model Constraints
- Only one default payment method per user
- Card expiration must be in future
- Provider method ID must be unique per provider

#### Custom Validation Methods
```python
def clean(self):
    if self.method_type in ['CREDIT_CARD', 'DEBIT_CARD']:
        if self.card_exp_month and self.card_exp_year:
            expiry_date = datetime(self.card_exp_year, self.card_exp_month, 1)
            if expiry_date <= datetime.now():
                raise ValidationError("Card expiration date must be in the future")
        
        if self.card_last4 and not self.card_last4.isdigit():
            raise ValidationError("Card last 4 digits must be numeric")
```

### 5.2 EscrowAccount Model

#### Field Validations
- **balance**: Non-negative
- **available_balance**: Non-negative
- **pending_balance**: Non-negative

#### Model Constraints
- Total balance = available + pending
- One escrow account per user per type
- Balance cannot be negative

#### Custom Validation Methods
```python
def clean(self):
    if self.balance < 0 or self.available_balance < 0 or self.pending_balance < 0:
        raise ValidationError("Balance values cannot be negative")
    
    if abs(self.balance - (self.available_balance + self.pending_balance)) > 0.01:
        raise ValidationError("Total balance must equal available plus pending balance")
```

### 5.3 Payment Model

#### Field Validations
- **amount**: Positive, max 99999.99
- **due_date**: Must be future date
- **invoice_number**: Required, unique, format: INV-YYYYMMDD-XXXXX

#### Model Constraints
- Amount must be positive
- Due date must be in future
- Invoice number must follow format
- Refund amount cannot exceed payment amount

#### Custom Validation Methods
```python
def clean(self):
    if self.amount <= 0:
        raise ValidationError("Payment amount must be positive")
    
    if self.due_date and self.due_date <= timezone.now().date():
        raise ValidationError("Due date must be in the future")
    
    if self.invoice_number and not re.match(r'^INV-\d{8}-\d{5}$', self.invoice_number):
        raise ValidationError("Invoice number must follow format: INV-YYYYMMDD-XXXXX")
    
    if self.refund_amount and self.refund_amount > self.amount:
        raise ValidationError("Refund amount cannot exceed payment amount")
```

## 6. Notifications App Validation Rules

### 6.1 NotificationType Model

#### Field Validations
- **name**: Required, unique, max 100 characters
- **code**: Required, unique, max 50 characters, alphanumeric with underscores
- **category**: Must be one of: 'REQUIREMENT', 'PROPOSAL', 'AWARD', 'PAYMENT', 'MESSAGE', 'SYSTEM', 'ADMIN'
- **priority**: Must be one of: 'LOW', 'NORMAL', 'HIGH', 'URGENT'

#### Model Constraints
- Name and code must be unique
- Code must be valid Python identifier
- Priority must be valid choice

#### Custom Validation Methods
```python
def clean(self):
    if self.code and not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', self.code):
        raise ValidationError("Code must be a valid Python identifier")
```

### 6.2 Notification Model

#### Field Validations
- **title**: Required, max 255 characters
- **message**: Required, max 5000 characters
- **action_text**: Max 100 characters if provided

#### Model Constraints
- Recipient must be specified
- Title and message cannot be empty
- Expiration must be in future if provided

#### Custom Validation Methods
```python
def clean(self):
    if not self.title.strip():
        raise ValidationError("Title cannot be empty")
    
    if not self.message.strip():
        raise ValidationError("Message cannot be empty")
    
    if self.expires_at and self.expires_at <= timezone.now():
        raise ValidationError("Expiration date must be in the future")
```

## 7. Cross-App Validation Rules

### 7.1 User Type Consistency
- Students can only have StudentProfile
- Tutors can only have TutorProfile
- Admins can only have AdminProfile
- User type determines accessible features

### 7.2 Business Logic Constraints
- Students cannot submit proposals
- Tutors cannot post requirements
- Only verified tutors can receive requirements
- Payment release requires completion confirmation
- Ratings only allowed after award completion

### 7.3 Data Integrity Rules
- Foreign key relationships must be valid
- Cascade delete rules must maintain integrity
- Soft delete for important records
- Audit trail for critical operations

## 8. Security Constraints

### 8.1 Input Validation
- All user inputs must be sanitized
- SQL injection prevention through ORM
- XSS prevention through proper escaping
- File upload validation and scanning

### 8.2 Access Control
- Users can only access their own data
- Role-based access control for admin functions
- API rate limiting
- Session security

### 8.3 Data Privacy
- Personal information encryption
- PII masking in logs
- GDPR compliance for data retention
- Right to be forgotten implementation

## 9. Performance Constraints

### 9.1 Query Limits
- Maximum result set sizes
- Query timeout limits
- Pagination requirements
- Caching strategies

### 9.2 Resource Limits
- File upload size limits
- Email sending rate limits
- API request rate limits
- Concurrent connection limits

## 10. Implementation Guidelines

### 10.1 Django Validation Implementation
```python
# Example of comprehensive model validation
class Requirement(models.Model):
    # ... fields ...
    
    def clean(self):
        super().clean()
        # Custom validation logic
        
    def save(self, *args, **kwargs):
        self.full_clean()  # Run all validations
        super().save(*args, **kwargs)
    
    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(budget_max__gte=models.F('budget_min')),
                name='budget_max_gte_budget_min'
            ),
            models.UniqueConstraint(
                fields=['slug'],
                name='unique_requirement_slug'
            )
        ]
```

### 10.2 Form Validation
```python
# Example of form validation
class RequirementForm(forms.ModelForm):
    class Meta:
        model = Requirement
        fields = ['title', 'description', 'subject', 'budget_min', 'budget_max']
    
    def clean(self):
        cleaned_data = super().clean()
        budget_min = cleaned_data.get('budget_min')
        budget_max = cleaned_data.get('budget_max')
        
        if budget_min and budget_max and budget_max < budget_min:
            raise forms.ValidationError("Maximum budget must be greater than minimum budget")
        
        return cleaned_data
```

### 10.3 API Validation
```python
# Example of API validation using DRF serializers
class RequirementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Requirement
        fields = '__all__'
    
    def validate(self, data):
        if data.get('budget_max') and data.get('budget_min'):
            if data['budget_max'] < data['budget_min']:
                raise serializers.ValidationError("Maximum budget must be greater than minimum budget")
        return data
```

## 11. Testing Validation Rules

### 11.1 Unit Tests
- Test all validation rules individually
- Test edge cases and boundary conditions
- Test custom validation methods
- Test model constraints

### 11.2 Integration Tests
- Test validation across model relationships
- Test validation in form submissions
- Test validation in API endpoints
- Test validation in admin interface

### 11.3 Performance Tests
- Test validation performance with large datasets
- Test concurrent validation scenarios
- Test memory usage during validation
- Test database constraint performance