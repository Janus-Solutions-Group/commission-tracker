# Commission Tracker

## Overview

Commission Tracker is a Flask-based web application designed to manage projects, employees, and track commission-based compensation. The application provides comprehensive tracking of employee hours, billing, and commission calculations across multiple projects and clients.

## System Architecture

### Backend Architecture
- **Framework**: Flask (Python web framework)
- **Database**: SQLAlchemy ORM with SQLite as default (configurable via DATABASE_URL)
- **Forms**: Flask-WTF for form handling and validation
- **Templates**: Jinja2 templating engine
- **Session Management**: Flask sessions with configurable secret key

### Frontend Architecture
- **UI Framework**: Bootstrap 5 with dark theme support
- **Icons**: Feather Icons for consistent iconography
- **Responsive Design**: Mobile-first approach using Bootstrap grid system
- **Theme**: Dark theme implementation with Bootstrap agent styling

### Application Structure
```
├── app.py              # Application factory and configuration
├── main.py             # Application entry point
├── models.py           # Database models and relationships
├── routes.py           # URL routing and view functions
├── forms.py            # WTForms for data validation
├── utils.py            # Helper functions and template filters
└── templates/          # HTML templates organized by feature
```

## Key Components

### Database Models
1. **Project**: Stores project information including client, dates, and calculates totals
2. **Employee**: Manages employee data with hourly rates and commission percentages
3. **ProjectStaff**: Junction table linking employees to projects with specific roles
4. **HoursEntry**: Tracks time worked and billed hours for commission calculations

### Core Features
1. **Dashboard**: Overview statistics and recent activity tracking
2. **Project Management**: CRUD operations for projects with client tracking
3. **Employee Management**: Employee profiles with commission rate configuration
4. **Time Tracking**: Hours entry system with worked vs billed hour differentiation
5. **Commission Analytics**: Detailed commission calculations and performance metrics

### Form Validation
- Project dates validation (end date after start date)
- Employee rate and commission percentage constraints
- Duplicate assignment prevention for project staff
- Required field validation across all forms

## Data Flow

### Commission Calculation Flow
1. Employees log hours worked and hours billed for specific projects
2. System calculates revenue: `hours_billed × hourly_rate`
3. Commission calculated: `revenue × commission_percentage ÷ 100`
4. Aggregated statistics displayed on dashboard and analytics pages

### User Interaction Flow
1. **Setup**: Create employees with rates and commission percentages
2. **Project Creation**: Add projects with client and date information
3. **Assignment**: Assign employees to projects with specific roles
4. **Time Entry**: Log worked and billed hours for accurate tracking
5. **Analytics**: View performance metrics and commission summaries

## External Dependencies

### Python Packages
- **Flask**: Web framework and core functionality
- **Flask-SQLAlchemy**: Database ORM and model management
- **Flask-WTF**: Form handling and CSRF protection
- **WTForms**: Form validation and rendering
- **Werkzeug**: WSGI utilities and proxy handling

### Frontend Dependencies
- **Bootstrap 5**: CSS framework for responsive design
- **Feather Icons**: Icon library for consistent UI elements
- **Bootstrap Agent Dark Theme**: Specialized dark theme styling

### Database Configuration
- **Default**: SQLite for development and simple deployments
- **Production**: Configurable via DATABASE_URL environment variable
- **Connection Pooling**: Implemented with pool recycling and pre-ping

## Deployment Strategy

### Environment Configuration
- **SESSION_SECRET**: Configurable session key (defaults to development key)
- **DATABASE_URL**: Flexible database connection string
- **Debug Mode**: Enabled for development, should be disabled in production

### Application Initialization
- Database tables created automatically on startup
- Models imported and registered with SQLAlchemy
- Routes registered with Flask application
- WSGI proxy fix applied for deployment behind reverse proxies

### Development Setup
- Application runs on host 0.0.0.0:5000 for container compatibility
- Debug mode enabled for development iteration
- Seed data script available for testing and demonstration

## Changelog
- June 30, 2025. Initial setup with dark theme
- July 1, 2025. Updated to modern light theme with sky blue accents and advanced styling

## Recent Changes
- **July 1, 2025**: Complete design overhaul implementing modern, fresh styling
  - Switched from dark to light theme with sky blue color palette
  - Added Inter font for improved typography
  - Implemented glassmorphism effects and advanced CSS animations
  - Enhanced cards with hover effects and gradient borders
  - Added smooth animations with staggered timing
  - Modernized statistics cards with floating icons and gradient text
  - Improved button styling with elevation effects
  - Enhanced table design with better spacing and hover states
  - Added custom scrollbar styling
  - Implemented responsive design patterns

## User Preferences

Preferred communication style: Simple, everyday language.
Design preferences: Modern, stunning, fresh design with light theme and sky blue accents.