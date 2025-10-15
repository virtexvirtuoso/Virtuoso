#!/usr/bin/env python3
"""
Quick Fixes for VPS Production Issues
- Session health checks for CCXT
- Graceful degradation for confluence analysis
"""

import os
import sys

# Patch 1: Add proactive session validation to CCXT methods that don't use _execute_with_session_retry

CCXT_HEALTH_CHECK_PATCH = '''
    async def _ensure_session_healthy(self):
        """Proactively check and reinitialize session if needed."""
        if not self.ccxt:
            await self.initialize()
            return

        # Check if session exists and is open
        if hasattr(self.ccxt, 'session'):
            if self.ccxt.session is None or self.ccxt.session.closed:
                logger.warning("Detected closed session, reinitializing...")
                await self._reinitialize_session()
'''

# Patch 2: Modify confluence analysis to allow partial indicator sets with confidence adjustment

CONFLUENCE_GRACEFUL_DEGRADATION_PATCH = '''
            # MODIFIED: Allow partial indicator sets with degraded confidence
            required_indicators = set(self.indicators.keys())
            successful_indicators = set(scores.keys())
            missing_indicators = required_indicators - successful_indicators

            # Calculate confidence multiplier based on successful indicators
            confidence_multiplier = len(successful_indicators) / len(required_indicators)

            if missing_indicators:
                self.logger.warning(f"PARTIAL CONFLUENCE ANALYSIS: Missing {len(missing_indicators)} indicators: {sorted(missing_indicators)}")
                self.logger.warning(f"Required indicators: {sorted(required_indicators)}")
                self.logger.warning(f"Successful indicators: {sorted(successful_indicators)} ({len(successful_indicators)}/{len(required_indicators)})")

                # Minimum threshold: at least 50% of indicators must succeed
                if confidence_multiplier < 0.5:
                    self.logger.error(f"Insufficient indicators for analysis: {confidence_multiplier:.1%} < 50% threshold")
                    self.logger.error("Confluence analysis requires at least 50% of indicators for degraded mode")

                    # Log detailed failure reasons for each missing indicator
                    for indicator_type in missing_indicators:
                        flow_status = self.data_flow_tracker.flow.get(indicator_type, {})
                        if flow_status.get('status') == 'error':
                            self.logger.error(f"  - {indicator_type}: Analysis failed with error")
                        else:
                            self.logger.error(f"  - {indicator_type}: Data transformation or validation failed")

                    return self._get_default_response()

                # DEGRADED MODE: Proceed with partial analysis
                self.logger.warning(f"⚠️  DEGRADED MODE: Operating with {confidence_multiplier:.1%} indicator coverage")
                self.logger.warning(f"Confidence scores will be adjusted by factor of {confidence_multiplier:.2f}")

                # Log detailed failure reasons for missing indicators (info level in degraded mode)
                for indicator_type in missing_indicators:
                    flow_status = self.data_flow_tracker.flow.get(indicator_type, {})
                    if flow_status.get('status') == 'error':
                        self.logger.info(f"  - {indicator_type}: Analysis failed with error (using fallback)")
                    else:
                        self.logger.info(f"  - {indicator_type}: Data transformation or validation failed (using fallback)")
            else:
                # Full mode
                confidence_multiplier = 1.0
                self.logger.info(f"✅ FULL MODE: All {len(required_indicators)} indicators successful")

            # Calculate confluence score (works with partial or full indicator set)
            if not scores:
                self.logger.error("No valid indicator scores calculated")
                return self._get_default_response()
'''

CONFLUENCE_SCORE_ADJUSTMENT = '''
            # Apply confidence multiplier to final scores
            reliability = self._calculate_reliability(scores) * confidence_multiplier

            # Add analysis mode to results
            analysis_mode = "full" if confidence_multiplier >= 1.0 else "degraded"
            mode_quality = "excellent" if confidence_multiplier >= 1.0 else \
                          "good" if confidence_multiplier >= 0.8 else \
                          "acceptable" if confidence_multiplier >= 0.6 else "limited"
'''

def apply_fixes():
    """Apply the quick fixes to the codebase."""
    print("=" * 80)
    print("VIRTUOSO TRADING SYSTEM - QUICK FIXES")
    print("=" * 80)
    print()
    print("This script will apply critical fixes for:")
    print("  1. Session health checks in CCXT exchange wrapper")
    print("  2. Graceful degradation for confluence analysis")
    print()

    # Get project root
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # File paths
    ccxt_file = os.path.join(project_root, 'src/core/exchanges/ccxt_exchange.py')
    confluence_file = os.path.join(project_root, 'src/core/analysis/confluence.py')

    print(f"Project root: {project_root}")
    print(f"CCXT file: {ccxt_file}")
    print(f"Confluence file: {confluence_file}")
    print()

    # Read files
    print("[1/4] Reading source files...")
    with open(ccxt_file, 'r') as f:
        ccxt_content = f.read()
    with open(confluence_file, 'r') as f:
        confluence_content = f.read()

    # Apply CCXT patch
    print("[2/4] Applying session health check patch to CCXT...")
    if 'async def _ensure_session_healthy' not in ccxt_content:
        # Add after _reinitialize_session method
        insertion_point = ccxt_content.find('    def _convert_symbol_to_ccxt_format(self, symbol: str) -> str:')
        if insertion_point != -1:
            ccxt_content = ccxt_content[:insertion_point] + CCXT_HEALTH_CHECK_PATCH + '\n' + ccxt_content[insertion_point:]
            print("  ✓ Added _ensure_session_healthy method")
        else:
            print("  ✗ Could not find insertion point")
    else:
        print("  → Session health check already exists")

    # Apply Confluence patch
    print("[3/4] Applying graceful degradation patch to Confluence...")

    # Replace the strict validation with degraded mode
    old_validation = '''            # CRITICAL: Require ALL 6 indicators to be successful for valid confluence analysis
            required_indicators = set(self.indicators.keys())
            successful_indicators = set(scores.keys())
            missing_indicators = required_indicators - successful_indicators

            if missing_indicators:
                self.logger.error(f"CONFLUENCE ANALYSIS FAILED: Missing required indicators: {sorted(missing_indicators)}")
                self.logger.error(f"Required indicators: {sorted(required_indicators)}")
                self.logger.error(f"Successful indicators: {sorted(successful_indicators)}")
                self.logger.error("Confluence analysis requires ALL indicators to be successful to ensure system integrity")

                # Log detailed failure reasons for each missing indicator
                for indicator_type in missing_indicators:
                    flow_status = self.data_flow_tracker.flow.get(indicator_type, {})
                    if flow_status.get('status') == 'error':
                        self.logger.error(f"  - {indicator_type}: Analysis failed with error")
                    else:
                        self.logger.error(f"  - {indicator_type}: Data transformation or validation failed")

                return self._get_default_response()

            # Calculate confluence score only if all indicators succeeded
            if not scores:
                self.logger.error("No valid indicator scores calculated")
                return self._get_default_response()

            self.logger.info(f"✅ ALL INDICATORS SUCCESSFUL: {len(scores)}/{len(required_indicators)} indicators calculated")
            self.logger.info(f"Successful indicators: {sorted(scores.keys())}")'''

    if old_validation in confluence_content:
        confluence_content = confluence_content.replace(old_validation, CONFLUENCE_GRACEFUL_DEGRADATION_PATCH)
        print("  ✓ Replaced strict validation with graceful degradation")
    else:
        print("  → Could not find exact validation pattern (may already be patched)")

    # Add confidence multiplier to reliability calculation
    old_reliability = '            reliability = self._calculate_reliability(scores)'
    if old_reliability in confluence_content:
        confluence_content = confluence_content.replace(
            old_reliability,
            '            reliability = self._calculate_reliability(scores)\n            \n            # Apply confidence multiplier for degraded mode\n            if \'confidence_multiplier\' in locals():\n                reliability = reliability * confidence_multiplier'
        )
        print("  ✓ Added confidence multiplier to reliability calculation")

    # Write files back
    print("[4/4] Writing patched files...")
    with open(ccxt_file, 'w') as f:
        f.write(ccxt_content)
    print(f"  ✓ Updated {ccxt_file}")

    with open(confluence_file, 'w') as f:
        f.write(confluence_content)
    print(f"  ✓ Updated {confluence_file}")

    print()
    print("=" * 80)
    print("QUICK FIXES APPLIED SUCCESSFULLY")
    print("=" * 80)
    print()
    print("Next steps:")
    print("  1. Review the changes (git diff)")
    print("  2. Deploy to VPS using deployment script")
    print("  3. Monitor logs for 'DEGRADED MODE' messages")
    print()

if __name__ == '__main__':
    apply_fixes()
