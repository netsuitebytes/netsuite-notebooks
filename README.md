# netsuite-notebooks

Python Jupyter notebooks for NetSuite REST API exploration and SuiteQL analysis.

Part of the [NetSuiteBytes](https://netsuitebytes.org) developer toolchain.

---

## Prerequisites

### Python
- Download from [python.org](https://www.python.org/downloads/) — Python 3.10 or newer
- During installation, check **"Add Python to PATH"**

### VS Code
- Download from [code.visualstudio.com](https://code.visualstudio.com/)

### VS Code Extensions

| Extension | Publisher | Purpose |
|---|---|---|
| **Python** | Microsoft | Python language support |
| **Jupyter** | Microsoft | Run `.ipynb` notebooks |
| **Pylance** | Microsoft | IntelliSense & type checking |

---

## Project Setup

### 1. Clone the Repository

```bash
git clone https://github.com/netsuitebytes/netsuite-notebooks.git
cd netsuite-notebooks
code .
```

### 2. Create a Virtual Environment

In the VS Code terminal (`Ctrl+``):

```bash
python -m venv .venv
```

#### Activate the Virtual Environment

**Windows PowerShell:**
```powershell
.venv\Scripts\activate
```

**Windows Command Prompt:**
```cmd
.venv\Scripts\activate.bat
```

**Mac/Linux:**
```bash
source .venv/bin/activate
```

> You should see `(.venv)` appear in your terminal prompt when activated.

---

### Windows PowerShell — Execution Policy Error

If you see this error on Windows when trying to activate:

```
.venv\Scripts\Activate.ps1 cannot be loaded. The file is not digitally signed.
```

Run this once to fix it for your user account:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Then activate normally.

---

### 3. Install Required Packages

```bash
pip install -r requirements.txt
```

| Package | Purpose |
|---|---|
| `requests` | Make HTTP calls to the NetSuite REST API |
| `requests-oauthlib` | Handle OAuth 1.0a authentication |
| `ipykernel` | Connect your virtual environment to Jupyter |
| `jupyter` | Jupyter notebook server and tooling |
| `python-dotenv` | Load credentials from a local `.env` file (sandbox/dev) |
| `pandas` | Load query results into a DataFrame |
| `openpyxl` | Export query results to Excel (`.xlsx`) |
| `azure-identity` | Azure credential chain (CLI login, managed identity, etc.) |
| `azure-keyvault-secrets` | Fetch secrets from Azure Key Vault (optional, production) |

---

## NetSuite Configuration

### Enable Token-Based Authentication

1. Go to **Setup → Company → Enable Features**
2. Click the **SuiteCloud** tab
3. Check **Token-Based Authentication**
4. Save

### Create an Integration Record

1. Go to **Setup → Integration → Manage Integrations → New**
2. Give it a name (e.g., `SuiteQL Notebooks`)
3. Check **Token-Based Authentication**
4. Save and copy the **Consumer Key** and **Consumer Secret**

### Required Role Permissions

The integration token must be associated with a role that has at least:

**Setup**
| Permission | Level |
|---|---|
| REST Web Services | Full |
| Log in using Access Tokens | Full |

**Transactions / Lists** — add View-level access to each record type your notebooks will query (Invoices, Sales Orders, Items, Accounts, Customers, etc.)

> Run `permissions_check.ipynb` after configuring a new environment to verify the role can reach each record type you need.

### Create an Access Token

1. Go to **Setup → Users/Roles → Access Tokens → New**
2. Select your **Integration**, **User**, and **Role**
3. Give it a name (e.g., `SuiteQL Notebooks Token`)
4. Save and copy the **Token ID** and **Token Secret**

> Tokens must be created by an administrator. The self-service option from Home → Set Preferences is no longer available in current NetSuite versions.

---

## Credentials Setup

Credentials are managed by `netsuite_auth.py`. It checks for `KEY_VAULT_URL` first; if not set it falls back to a local `.env` file. This lets sandbox development work with local files while production credentials stay off-disk in the vault.

### Option A — Local `.env` File (sandbox / development)

Copy `.env.example` to `.env.sandbox2` (or `.env.production`) and fill in your values:

```bash
cp .env.example .env.sandbox2
```

```env
NS_ACCOUNT_ID=your_account_id
NS_CONSUMER_KEY=your_consumer_key
NS_CONSUMER_SECRET=your_consumer_secret
NS_TOKEN_ID=your_token_id
NS_TOKEN_SECRET=your_token_secret
```

> **Account ID format:** Use `1234567` for production or `1234567-sb2` for sandbox environments.

> ⚠️ **Never commit `.env*` files to source control.** All `.env*` files are covered by `.gitignore`.

### Option B — Azure Key Vault (production / CI)

Store each credential as a secret in Azure Key Vault using this naming convention (replace `{env}` with `sandbox2` or `production`):

```
ns-{env}-account-id
ns-{env}-consumer-key
ns-{env}-consumer-secret
ns-{env}-token-id
ns-{env}-token-secret
```

Set the vault URL and target environment before running notebooks:

**Windows Command Prompt:**
```cmd
set KEY_VAULT_URL=https://your-vault-name.vault.azure.net/
set NETSUITE_ENV=production
```

**Mac/Linux:**
```bash
export KEY_VAULT_URL=https://your-vault-name.vault.azure.net/
export NETSUITE_ENV=production
```

Authenticate once with the Azure CLI:

```bash
az login
```

`DefaultAzureCredential` will automatically pick up the CLI login. On Azure-hosted compute it uses the assigned managed identity instead.

### Selecting the Environment in a Notebook

`netsuite_auth.py` defaults to `NETSUITE_ENV="sandbox2"`. Most notebooks just need:

```python
from netsuite_auth import get_auth, run_suiteql, run_suiteql_all

auth, BASE_URL = get_auth()
```

To target a different environment, override `NETSUITE_ENV` **before** the import:

```python
import os
os.environ["NETSUITE_ENV"] = "production"

from netsuite_auth import get_auth, run_suiteql, run_suiteql_all

auth, BASE_URL = get_auth()
```

---

## Notebooks

| Notebook | What it does |
|---|---|
| `permissions_check.ipynb` | Verify the configured role has View access to each record type you plan to query |
| `item_master_schema.ipynb` | Discover all queryable fields on the `item` record type |
| `sales_order_query.ipynb` | Query and export sales orders with line-level detail |
| `transaction_delete.ipynb` | Delete transactions by type and date range via the REST Record API |

### Open a Notebook

1. Open the notebook file in VS Code
2. In the top-right corner, click **Select Kernel** → **Python Environments...** → select **.venv**
3. Run cells with `Shift+Enter`

---

## Project Structure

```
netsuite-notebooks/
├── .env.sandbox2            ← sandbox credentials (never commit!)
├── .env.production          ← production credentials (never commit!)
├── .env.example             ← template — copy and fill in your values
├── .gitignore
├── README.md
├── requirements.txt
├── netsuite_auth.py         ← credential loader (Key Vault or .env)
├── permissions_check.ipynb
├── item_master_schema.ipynb
├── sales_order_query.ipynb
└── transaction_delete.ipynb
```

---

## Contributing

This is a community project. If you have a notebook that solves a real NetSuite problem, open a PR or share it in [Discussions](https://github.com/orgs/netsuitebytes/discussions).

---

## License

MIT

---

*Part of [NetSuiteBytes](https://netsuitebytes.org) — built by [Literal Data LLC](https://literaldata.com)*
