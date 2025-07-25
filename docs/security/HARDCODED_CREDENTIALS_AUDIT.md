# Hardcoded Credentials Security Audit Report

**Date:** July 24, 2025  
**Severity:** HIGH - Immediate action required

## Executive Summary

A comprehensive security audit of the codebase revealed multiple instances of hardcoded credentials and sensitive information that pose significant security risks. These findings require immediate remediation to prevent unauthorized access and potential data breaches.

## Critical Findings

### 1. Discord Webhook URLs (HIGH SEVERITY)

**Hardcoded Production Webhooks Found:**

1. **File:** `/scripts/testing/test_alert_consistency.py`
   - Line 32
   - Webhook: `https://discord.com/api/webhooks/13756475279149630466/mLWWh-FDHOr7ZE3xBNFQh7DqxL5IqJ6dWLpRzCGNW2vPbIgW7Qx8KHVvEHMqnA6P_D9F`
   - **Risk:** This appears to be a real Discord webhook that could be used to send unauthorized messages

2. **File:** `/.env`
   - Line 42: `DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/1375647527914963097/aSjg9CRhNN-9ji8mSuQ0riodi2HF2dYPUGJeKzq7fOzzLuAOpRZqFCNT-Wpg_Vu3rf9C`
   - Line 43: `SYSTEM_ALERTS_WEBHOOK_URL=https://discord.com/api/webhooks/1379097202613420163/IJXNvNxw09zXGvQe2oZZ-8TwYc91hZH4PqD6XtVEQa5fH6TpBt9hBLuTZiejUPjW9m8i`
   - **Risk:** Production Discord webhooks exposed in environment file

### 2. API Credentials (HIGH SEVERITY)

**Bybit API Credentials:**

1. **File:** `/tests/reporting/test_market_report.py`
   - Line 51: `bybit_api_key = 'TjaG5KducWssxy9Z1m'`
   - Line 52: `bybit_api_secret = '6x6VAFOrwhc4EJJNmda7PdEYYKbcndo6povm'`
   - **Risk:** Hardcoded API credentials could provide unauthorized access to trading accounts

2. **File:** `/.env`
   - Line 29: `BYBIT_API_KEY=yTjaG5KducWssxy9Z1m`
   - Line 30: `BYBIT_API_SECRET=6x6VAFOrwhc4EJJNmda7PdEYYKbcndo6povm`
   - **Risk:** Production API credentials exposed in environment file

### 3. Database Tokens (HIGH SEVERITY)

**InfluxDB Token:**

1. **File:** `/.env`
   - Line 12: `INFLUXDB_TOKEN=auUwotDWSbRMNkZLAptfwRv8_lOm_GGJHzmKirgv-Zj8xZya4T6NWYaVqZGNpfaMyxsmtdgBtpaVNtx7PIxNbQ==`
   - **Risk:** Database access token exposed

2. **Multiple Shell Scripts:**
   - `/scripts/set_influxdb_env.sh` (lines 7, 34)
   - `/scripts/update_credentials.sh` (line 10)
   - `/scripts/restart_with_fixed_db.sh` (line 8)
   - **Risk:** Same InfluxDB token hardcoded in multiple shell scripts

### 4. JWT Secret (MEDIUM SEVERITY)

**File:** `/.env`
- Line 33: `JWT_SECRET_KEY=your_jwt_secret_here`
- **Risk:** Default/weak JWT secret that hasn't been changed from placeholder

### 5. Test Credentials (LOW SEVERITY)

Multiple test files contain placeholder credentials:
- `/tests/validation/test_comprehensive_validation_fixes.py`
- `/tests/validation/test_keyerror_fixes.py`
- Various test files with `test_key` and `test_secret`

## Recommendations

### Immediate Actions Required:

1. **Rotate All Credentials:**
   - Immediately rotate all Discord webhook URLs
   - Regenerate Bybit API keys
   - Create new InfluxDB token
   - Generate a strong JWT secret

2. **Remove Hardcoded Credentials:**
   - Remove all hardcoded credentials from source code
   - Update `.gitignore` to exclude `.env` files
   - Remove `.env` file from version control

3. **Implement Secure Credential Management:**
   - Use environment variables exclusively
   - Consider using a secrets management service (AWS Secrets Manager, HashiCorp Vault)
   - Never commit credentials to version control

4. **Update Code Patterns:**
   ```python
   # Bad - Hardcoded
   api_key = 'TjaG5KducWssxy9Z1m'
   
   # Good - Environment variable
   api_key = os.environ.get('BYBIT_API_KEY')
   if not api_key:
       raise ValueError("BYBIT_API_KEY environment variable not set")
   ```

5. **Security Best Practices:**
   - Add pre-commit hooks to scan for credentials
   - Use `.env.example` files with placeholder values
   - Document required environment variables without exposing actual values
   - Regular security audits

### Git History Cleanup:

Since these credentials are already in git history, you should:
1. Use `git filter-branch` or BFG Repo-Cleaner to remove sensitive data from history
2. Force push the cleaned repository
3. Ensure all team members re-clone the repository

## Affected Files Summary

- Production credentials: 7 files
- Test credentials: 10+ files  
- Shell scripts: 4 files
- Configuration files: 1 file (.env)

## Conclusion

This audit reveals significant security vulnerabilities that require immediate attention. All production credentials should be considered compromised and must be rotated immediately. Going forward, implement strict policies against committing any credentials to version control.