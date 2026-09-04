# wazuhscatune

A helper for Wazuh Security Configuration Assessment (SCA) to create a custom SCA based on loosening.

## Overview

SCA Guide is available in two interfaces:

1. **Web Application** - Modern, user-friendly web interface with card-based UI
2. **CLI Application** - Terminal-based interface for automation and scripting

The principle behind this tool is that one must stick to a hardening guide, then analyze the requirements to create a list of loosening factors. Every environment is different, and every environment must stick to a baseline. A loosening guide is better than a custom made hardening guide in most cases.

Both interfaces guide you through each requirement one by one. When you want to add an exception, you must specify a justification. This creates a documented list of exceptions for your environment.

## Installation

Install the required dependencies:

```bash
pip install -r requirements.txt
```

For development:

```bash
pip install -r requirements.dev.txt
```

## Web Application

### Starting the Web Application

Run the Flask application:

```bash
python app.py
```

Or using Flask CLI:

```bash
flask run
```

The web application will be available at `http://localhost:5000`

### Web Application Features

- **Modern Card-Based Interface**: Review checks in an intuitive card grid layout
- **Interactive Modals**: View detailed check information with full descriptions, rationale, remediation, and compliance frameworks
- **Real-Time Filtering**: Filter checks by status (included/excluded/unreviewed), impact level, compliance framework, or search text
- **Progress Tracking**: Visual progress indicator showing reviewed and excluded checks
- **Auto-Save**: Automatic draft saving every 30 seconds plus manual save option
- **Session Management**: Persistent sessions with 24-hour timeout
- **Export to ZIP**: Download custom SCA policy, loosening YAML, and loosening Markdown in a single ZIP file

### Web Application Workflow

1. **Upload**: Upload a baseline SCA YAML file and provide custom policy name and description
2. **Review**: Review each check in the card grid, click to view details in modal
3. **Decide**: For each check, choose to include or exclude with justification (required for exclusions)
4. **Approve**: Review summary statistics and all excluded checks with justifications
5. **Export**: Download ZIP file containing custom SCA policy and loosening documentation

### Screenshots

#### Upload Page
![Upload Page](https://github.com/user-attachments/assets/2aa6d09e-cfe2-4c9d-a17c-c2df63814110)

#### Review Page with Card Grid
![Review Page](https://github.com/user-attachments/assets/e66cb07b-d34a-4700-9e0d-4431bf11a6df)

#### Check Details Modal
![Modal View](https://github.com/user-attachments/assets/0b2587a9-8d30-41ea-a43c-225361db1350)

#### Approval Page
![Approval Page](https://github.com/user-attachments/assets/827dc2b9-4e6b-4ca5-ae41-06570d12f3b7)

### Environment Variables

The web application can be configured using environment variables:

- `SECRET_KEY`: Secret key for session encryption. In development, if this variable is not set, a new random key is generated each time the application starts, which invalidates any existing sessions after a restart. In production, you **must** set this to a strong, stable value.
- `FLASK_ENV`: Flask environment (development/production)
- `FLASK_APP`: Flask application entry point (default: 'app.py')

**Important**: In production environments, always set a strong, unpredictable `SECRET_KEY` and do not rely on the development fallback behavior.

## CLI Application

### Usage

```bash
usage: wazuhscatune.py [-h] --baseline BASELINE --custom CUSTOM --loosening LOOSENING

wazuhscatune (0.1) is a helper for Wazuh Security Configuration Assessment (SCA) to create a custom SCA based on
loosening.

options:
  -h, --help            show this help message and exit
  --baseline BASELINE, -b BASELINE
                        Path to the Wazuh SCA (yaml) file to start with
  --custom CUSTOM, -c CUSTOM
                        Path to the custom Wazuh SCA (yaml) file to save
  --loosening LOOSENING, -l LOOSENING
                        Path to the list of suppression decisions (markdown + yaml) from the Wazuh SCA file
```

### Sample CLI Usage

```bash
python wazuhscatune.py -b data/windows/cis_win2022.yml -c custom_win2022.yml -l loosening_win2022.yml
```

The CLI application will guide you through each check interactively in the terminal.

## What is next?

When you have a custom SCA file created, follow [Wazuh documentation](https://documentation.wazuh.com/current/user-manual/capabilities/sec-config-assessment/creating-custom-policies.html).

It is better to store the loosening file next to it as a helper, and in whatever documentation tool or source code repository you use in your team.

## Troubleshooting

### Web Application

**Port already in use**:
```bash
# Change the port in app.py or use Flask CLI
flask run --port 5001
```

**Session errors**:
- Ensure the `flask_session` directory has write permissions
- Check that `SECRET_KEY` is set properly

**File upload errors**:
- Verify file is valid YAML format
- Ensure file size is under 16MB
- Check that `uploads` directory exists and has write permissions

### CLI Application

**YAML parsing errors**:
- Verify the baseline SCA file is valid YAML
- Ensure all required fields are present (policy, checks)

## License

This project is licensed under the GNU General Public License (GPL).
