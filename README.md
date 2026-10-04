# ShareCycle

ShareCycle is a web-based donation platform that connects people who have unused items with people who need them.

## Problem Statement

Many usable items such as books, clothes, study materials, furniture, electronics and household items are unused or discarded, while students and other people may need the same items.

ShareCycle provides a platform to connect donors and recipients and uses a matching system to identify relevant items.

## Objectives

- Allow users to register and log in.
- Allow donors to list unused items.
- Allow recipients to search for available items.
- Match items with recipient requirements.
- Allow recipients to request items.
- Allow donors to accept or reject requests.
- Track donation status.
- Provide notifications.
- Provide administrators with management and analytics features.

## Main Features

- User Registration and Login
- Donor Dashboard
- Recipient Dashboard
- Item Listing
- Item Search
- Item Image Upload
- Matching System
- Donation Requests
- Request Approval/Rejection
- Donation Tracking
- Notifications
- User Profile
- Admin Dashboard
- Admin User Management
- Admin Item Management
- Analytics
- Impact Statistics

## Matching System

ShareCycle calculates a matching score using factors such as:

- Category matching
- Keyword matching
- Item title relevance
- Location matching
- Item condition

The system also provides reasons explaining why an item matches a recipient's requirement.

## Technology Stack

### Frontend
- HTML
- CSS
- JavaScript

### Backend
- Python
- Flask

### Database
- SQLite

### Security
- Password hashing
- Session-based authentication
- Secure image filenames
- File type validation
- Maximum upload size
- Environment-based secret key

## Project Structure

```text
ShareCycle/
├── app.py
├── database.py
├── matching.py
├── requirements.txt
├── .gitignore
├── .env
├── sharecycle.db
├── static/
├── templates/
├── uploads/
└── venv/