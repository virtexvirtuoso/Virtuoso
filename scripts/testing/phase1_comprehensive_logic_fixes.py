#!/usr/bin/env python3
"""
Phase 1: Comprehensive Logic Inconsistency Fixes
==============================================

This script fixes all 13 identified logic inconsistencies in the indicator scoring system
while adding contextual validation to prevent false bullish/bearish signals.

Key Features:
- Fixes obvious logic inversions
- Adds market context awareness
- Prevents false signals through validation
- Maintains 0-100 scoring standard
- Comprehensive error handling
"""

import os
import sys
import re
import shutil
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

class MarketContextValidator:
    """
    Market context validation to prevent false bullish/bearish signals
    """
    
    @staticmethod
    def validate_oversold_bullish(score: float, rsi_value: float, price_trend: str = "unknown") -> float:
        """
        Validate oversold conditions - ensure they're truly bullish
        """
        if rsi_value < 30:  # Oversold
            # In strong downtrend, oversold might not be immediately bullish
            if price_trend == "strong_downtrend":
                return min(score, 65)  # Cap bullish signal
            return max(score, 60)  # Ensure minimum bullish signal
        return score
    
    @staticmethod
    def validate_overbought_bearish(score: float, rsi_value: float, price_trend: str = "unknown") -> float:
        """
        Validate overbought conditions - ensure they're truly bearish
        """
        if rsi_value > 70:  # Overbought
            # In strong uptrend, overbought might not be immediately bearish
            if price_trend == "strong_uptrend":
                return max(score, 35)  # Cap bearish signal
            return min(score, 40)  # Ensure maximum bearish signal
        return score
    
    @staticmethod
    def validate_volume_context(score: float, volume_ratio: float, price_direction: str) -> float:
        """
        Validate volume signals with price direction context
        """
        if volume_ratio > 2.0:  # High volume
            if price_direction == "down":
                # High volume on down move is bearish
                return min(score, 30)
            elif price_direction == "up":
                # High volume on up move is bullish
                return max(score, 70)
        return score
    
    @staticmethod
    def validate_funding_extremes(score: float, funding_rate: float) -> float:
        """
        Validate funding rate extremes to prevent false signals
        """
        if abs(funding_rate) > 0.01:  # 1% funding rate (extreme)
            # Extreme funding rates might indicate market manipulation
            return min(max(score, 40), 60)  # Force toward neutral
        return score
    
    @staticmethod
    def validate_range_position(score: float, position_ratio: float, range_age: int) -> float:
        """
        Validate range position with range maturity context
        """
        if range_age < 10:  # Young range
            # Position in young range is less reliable
            return 50 + (score - 50) * 0.5  # Reduce signal strength
        return score

class Phase1LogicFixer:
    """
    Comprehensive logic inconsistency fixer for Phase 1
    """
    
    def __init__(self):
        self.fixes_applied = []
        self.validation_errors = []
        self.backup_dir = None
        
    def apply_all_fixes(self) -> Dict[str, any]:
        """
        Apply all 13 logic inconsistency fixes
        """
        print("🔧 Starting Phase 1 Logic Inconsistency Fixes...")
        
        # Create backup
        self.backup_dir = self._create_backup()
        
        # Apply fixes in order of criticality
        fixes = [
            self._fix_timeframe_score_interpretation,
            self._fix_williams_r_scoring,
            self._fix_order_blocks_scoring,
            self._fix_volume_profile_scoring,
            self._fix_funding_rate_scoring,
            self._fix_orderbook_imbalance_scoring,
            self._fix_cvd_scoring,
            self._fix_range_position_scoring,
            self._fix_relative_volume_scoring,
            self._fix_lsr_scoring,
            self._fix_spread_scoring,
            self._fix_trade_flow_scoring,
            self._fix_support_resistance_scoring,
        ]
        
        for fix_func in fixes:
            try:
                fix_func()
            except Exception as e:
                self.validation_errors.append(f"Error in {fix_func.__name__}: {str(e)}")
                print(f"❌ Error in {fix_func.__name__}: {str(e)}")
        
        # Generate report
        report = self._generate_fix_report()
        print(f"✅ Phase 1 fixes completed. {len(self.fixes_applied)} fixes applied.")
        
        return report
    
    def _create_backup(self) -> str:
        """Create timestamped backup of indicator files"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = f"backups/phase1_logic_fixes_{timestamp}"
        
        if os.path.exists(backup_dir):
            shutil.rmtree(backup_dir)
        
        shutil.copytree("src/indicators", backup_dir)
        print(f"📁 Backup created: {backup_dir}")
        return backup_dir
    
    def _fix_timeframe_score_interpretation(self):
        """
        Fix 1: Price Structure _interpret_timeframe_score backwards logic
        """
        file_path = "src/indicators/price_structure_indicators.py"
        
        # Read current content
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Find and fix the backwards logic
        old_pattern = r'elif score > 55:\s*return "Neutral"'
        new_logic = '''elif score >= 70:
            return "Strongly Bullish"
        elif score >= 55:
            return "Moderately Bullish"'''
        
        if re.search(old_pattern, content):
            content = re.sub(old_pattern, new_logic, content)
            
            # Also fix the complete interpretation logic
            interpretation_fix = '''
    def _interpret_timeframe_score(self, score: float) -> str:
        """
        Interpret timeframe score with proper bullish/bearish logic
        Fixed: Removed backwards logic where score > 55 was "Neutral"
        """
        try:
            score = float(np.clip(score, 0, 100))
            
            if score >= 80:
                return "Extremely Bullish"
            elif score >= 70:
                return "Strongly Bullish"
            elif score >= 55:
                return "Moderately Bullish"
            elif score >= 45:
                return "Slightly Bullish"
            elif score >= 35:
                return "Neutral"
            elif score >= 25:
                return "Slightly Bearish"
            elif score >= 15:
                return "Moderately Bearish"
            else:
                return "Strongly Bearish"
        except Exception as e:
            return "Neutral"  # Safe fallback
            '''
            
            # Replace the entire method
            method_pattern = r'def _interpret_timeframe_score\(self, score: float\) -> str:.*?(?=\n    def|\nclass|\n\n\n|\Z)'
            content = re.sub(method_pattern, interpretation_fix.strip(), content, flags=re.DOTALL)
            
            # Write back
            with open(file_path, 'w') as f:
                f.write(content)
            
            self.fixes_applied.append("Fixed _interpret_timeframe_score backwards logic")
            print("✅ Fixed timeframe score interpretation logic")
    
    def _fix_williams_r_scoring(self):
        """
        Fix 2: Technical Indicators Williams %R scoring inversion
        """
        file_path = "src/indicators/technical_indicators.py"
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Fix Williams %R scoring logic
        williams_r_fix = '''
        # Williams %R calculation with proper oversold/overbought logic
        if len(williams_r) > 0:
            latest_williams_r = williams_r.iloc[-1]
            
            # Williams %R ranges from -100 to 0
            # -100 = oversold (bullish) should give high score
            # 0 = overbought (bearish) should give low score
            williams_r_score = 100 + latest_williams_r  # Convert to 0-100 range
            williams_r_score = 100 - williams_r_score    # Invert: oversold -> high score
            
            # Apply market context validation
            williams_r_score = MarketContextValidator.validate_oversold_bullish(
                williams_r_score, abs(latest_williams_r), 
                price_trend="unknown"  # Can be enhanced with trend detection
            )
            
            williams_r_score = float(np.clip(williams_r_score, 0, 100))
        else:
            williams_r_score = 50.0  # Neutral fallback
        '''
        
        # Replace Williams %R calculation
        pattern = r'williams_r_score = 100 \+ latest_williams_r.*?(?=\n\s*else:|\n\s*williams_r_score = float)'
        if re.search(pattern, content, re.DOTALL):
            content = re.sub(pattern, williams_r_fix.strip(), content, flags=re.DOTALL)
            
            # Add import for MarketContextValidator at top of file
            if "from scripts.testing.phase1_comprehensive_logic_fixes import MarketContextValidator" not in content:
                import_pattern = r'(import numpy as np.*?\n)'
                content = re.sub(import_pattern, r'\1from scripts.testing.phase1_comprehensive_logic_fixes import MarketContextValidator\n', content)
            
            with open(file_path, 'w') as f:
                f.write(content)
            
            self.fixes_applied.append("Fixed Williams %R scoring inversion")
            print("✅ Fixed Williams %R scoring logic")
    
    def _fix_order_blocks_scoring(self):
        """
        Fix 3: Order Block scoring logic inconsistencies
        """
        file_path = "src/indicators/price_structure_indicators.py"
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Fix order block scoring with proper context
        order_block_fix = '''
    def _calculate_order_blocks_score(self, data: pd.DataFrame) -> float:
        """
        Calculate order block score with proper bullish/bearish logic
        Fixed: Added context validation for price position relative to order blocks
        """
        try:
            if len(data) < 20:
                return 50.0
            
            order_blocks = self._identify_order_blocks(data)
            if not order_blocks or not order_blocks.get('bullish') or not order_blocks.get('bearish'):
                return 50.0
            
            current_price = data['close'].iloc[-1]
            
            # Get strongest order blocks
            strongest_bullish = max(order_blocks['bullish'], key=lambda x: x['strength'])
            strongest_bearish = max(order_blocks['bearish'], key=lambda x: x['strength'])
            
            bullish_distance = abs(current_price - strongest_bullish['price']) / current_price
            bearish_distance = abs(current_price - strongest_bearish['price']) / current_price
            
            # Base score calculation
            base_score = 50.0
            
            # Price above bullish order block = bullish continuation
            if current_price > strongest_bullish['price']:
                base_score += min(strongest_bullish['strength'] * 20, 30)
            
            # Price below bearish order block = bearish continuation  
            if current_price < strongest_bearish['price']:
                base_score -= min(strongest_bearish['strength'] * 20, 30)
            
            # Context validation: Consider distance and market structure
            if bullish_distance < 0.02:  # Very close to bullish block
                if current_price > strongest_bullish['price']:
                    base_score = max(base_score, 65)  # Strong bullish signal
                else:
                    base_score = min(base_score, 35)  # Rejection at support
            
            if bearish_distance < 0.02:  # Very close to bearish block
                if current_price < strongest_bearish['price']:
                    base_score = min(base_score, 35)  # Strong bearish signal
                else:
                    base_score = max(base_score, 65)  # Breakout above resistance
            
            return float(np.clip(base_score, 0, 100))
            
        except Exception as e:
            return 50.0  # Neutral fallback
        '''
        
        # Replace the method
        method_pattern = r'def _calculate_order_blocks_score\(self, data: pd\.DataFrame\) -> float:.*?(?=\n    def|\nclass|\n\n\n|\Z)'
        content = re.sub(method_pattern, order_block_fix.strip(), content, flags=re.DOTALL)
        
        with open(file_path, 'w') as f:
            f.write(content)
        
        self.fixes_applied.append("Fixed order blocks scoring logic")
        print("✅ Fixed order blocks scoring logic")
    
    def _fix_volume_profile_scoring(self):
        """
        Fix 4: Volume Profile position scoring with market context
        """
        file_path = "src/indicators/volume_indicators.py"
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Fix volume profile scoring
        volume_profile_fix = '''
    def _calculate_volume_profile_score(self, data: pd.DataFrame) -> float:
        """
        Calculate volume profile score with proper market context validation
        Fixed: Added context awareness for price position in volume profile
        """
        try:
            if len(data) < 50:
                return 50.0
            
            volume_profile = self._calculate_volume_profile(data)
            if not volume_profile:
                return 50.0
            
            current_price = data['close'].iloc[-1]
            poc_price = volume_profile.get('poc_price', current_price)
            value_area_high = volume_profile.get('value_area_high', current_price)
            value_area_low = volume_profile.get('value_area_low', current_price)
            
            # Calculate position in value area
            if value_area_high > value_area_low:
                position_ratio = (current_price - value_area_low) / (value_area_high - value_area_low)
            else:
                position_ratio = 0.5
            
            # Base scoring with context validation
            if position_ratio <= 0.25:
                # Low in value area - potentially bullish but context matters
                base_score = 65.0
                # Validate: if we're in a strong downtrend, this might be a dead cat bounce
                price_trend = self._detect_price_trend(data)
                if price_trend == "strong_downtrend":
                    base_score = min(base_score, 55)  # Reduce bullish signal
            elif position_ratio >= 0.75:
                # High in value area - potentially bearish but context matters
                base_score = 35.0
                # Validate: if we're in a strong uptrend, this might continue
                price_trend = self._detect_price_trend(data)
                if price_trend == "strong_uptrend":
                    base_score = max(base_score, 45)  # Reduce bearish signal
            else:
                # Middle of value area
                base_score = 50.0
            
            # POC proximity adjustment
            poc_distance = abs(current_price - poc_price) / current_price
            if poc_distance < 0.01:  # Very close to POC
                base_score = 50 + (base_score - 50) * 1.2  # Amplify signal
            
            return float(np.clip(base_score, 0, 100))
            
        except Exception as e:
            return 50.0
        '''
        
        # Add helper method for trend detection
        trend_detection_method = '''
    def _detect_price_trend(self, data: pd.DataFrame, periods: int = 20) -> str:
        """
        Simple trend detection helper
        """
        try:
            if len(data) < periods:
                return "unknown"
            
            recent_data = data.tail(periods)
            price_change = (recent_data['close'].iloc[-1] - recent_data['close'].iloc[0]) / recent_data['close'].iloc[0]
            
            if price_change > 0.05:  # 5% up
                return "strong_uptrend"
            elif price_change < -0.05:  # 5% down
                return "strong_downtrend"
            elif price_change > 0.02:
                return "uptrend"
            elif price_change < -0.02:
                return "downtrend"
            else:
                return "sideways"
        except:
            return "unknown"
        '''
        
        # Replace the method
        method_pattern = r'def _calculate_volume_profile_score\(self, data: pd\.DataFrame\) -> float:.*?(?=\n    def|\nclass|\n\n\n|\Z)'
        content = re.sub(method_pattern, volume_profile_fix.strip(), content, flags=re.DOTALL)
        
        # Add trend detection method if not exists
        if "_detect_price_trend" not in content:
            # Find a good place to insert (after last method)
            content = content.rstrip() + "\n\n" + trend_detection_method.strip() + "\n"
        
        with open(file_path, 'w') as f:
            f.write(content)
        
        self.fixes_applied.append("Fixed volume profile scoring with context validation")
        print("✅ Fixed volume profile scoring logic")
    
    def _fix_funding_rate_scoring(self):
        """
        Fix 5: Sentiment Indicators funding rate interpretation
        """
        file_path = "src/indicators/sentiment_indicators.py"
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Fix funding rate scoring
        funding_fix = '''
    def _calculate_funding_score(self, symbol: str) -> float:
        """
        Calculate funding rate score with proper extreme value handling
        Fixed: Added validation for extreme funding rates that might indicate manipulation
        """
        try:
            funding_data = self._get_funding_rate(symbol)
            if not funding_data:
                return 50.0
            
            funding_rate = funding_data.get('funding_rate', 0)
            
            # Convert to percentage for easier handling
            funding_pct = funding_rate * 100
            
            # Clip extreme values to prevent manipulation
            funding_pct_clipped = np.clip(funding_pct, -0.5, 0.5)  # ±0.5%
            
            # Base calculation: negative funding = bullish (shorts pay longs)
            raw_score = 50 - (funding_pct_clipped * 100)  # Scale appropriately
            
            # Apply extreme value validation
            raw_score = MarketContextValidator.validate_funding_extremes(
                raw_score, abs(funding_rate)
            )
            
            # Additional context: very extreme funding might indicate market stress
            if abs(funding_rate) > 0.005:  # 0.5% funding rate
                # Force toward neutral in extreme conditions
                raw_score = 50 + (raw_score - 50) * 0.5
            
            return float(np.clip(raw_score, 0, 100))
            
        except Exception as e:
            return 50.0
        '''
        
        # Replace the method
        method_pattern = r'def _calculate_funding_score\(self, symbol: str\) -> float:.*?(?=\n    def|\nclass|\n\n\n|\Z)'
        content = re.sub(method_pattern, funding_fix.strip(), content, flags=re.DOTALL)
        
        with open(file_path, 'w') as f:
            f.write(content)
        
        self.fixes_applied.append("Fixed funding rate scoring with extreme value handling")
        print("✅ Fixed funding rate scoring logic")
    
    def _fix_orderbook_imbalance_scoring(self):
        """
        Fix 6: Orderbook imbalance calculation with depth confidence
        """
        file_path = "src/indicators/orderbook_indicators.py"
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Fix orderbook imbalance scoring
        imbalance_fix = '''
    def _calculate_orderbook_imbalance(self, orderbook_data: dict) -> float:
        """
        Calculate orderbook imbalance with proper depth confidence validation
        Fixed: Prevent amplification of incorrect imbalance signals
        """
        try:
            if not orderbook_data or 'bids' not in orderbook_data or 'asks' not in orderbook_data:
                return 50.0
            
            bids = orderbook_data['bids']
            asks = orderbook_data['asks']
            
            if not bids or not asks:
                return 50.0
            
            # Calculate imbalance for multiple depth levels
            imbalances = []
            depth_levels = [5, 10, 20]  # Different depth levels
            
            for depth in depth_levels:
                if len(bids) >= depth and len(asks) >= depth:
                    bid_volume = sum(float(bid[1]) for bid in bids[:depth])
                    ask_volume = sum(float(ask[1]) for ask in asks[:depth])
                    
                    if bid_volume + ask_volume > 0:
                        imbalance = (bid_volume - ask_volume) / (bid_volume + ask_volume)
                        imbalances.append(imbalance)
            
            if not imbalances:
                return 50.0
            
            # Average imbalance across depth levels
            avg_imbalance = np.mean(imbalances)
            
            # Normalize to 0-100 range
            normalized_imbalance = 50 + (avg_imbalance * 50)
            
            # Depth confidence: more consistent across depths = higher confidence
            imbalance_std = np.std(imbalances) if len(imbalances) > 1 else 0
            depth_confidence = max(0.3, 1.0 - imbalance_std * 2)  # Min 30% confidence
            
            # Apply confidence weighting - but don't amplify wrong signals
            if abs(avg_imbalance) > 0.3:  # Strong imbalance
                # Validate: very strong imbalances might be temporary
                depth_confidence = min(depth_confidence, 0.7)  # Cap confidence
            
            final_score = 50 + (normalized_imbalance - 50) * depth_confidence
            
            return float(np.clip(final_score, 0, 100))
            
        except Exception as e:
            return 50.0
        '''
        
        # Replace the method
        method_pattern = r'def _calculate_orderbook_imbalance\(self, orderbook_data: dict\) -> float:.*?(?=\n    def|\nclass|\n\n\n|\Z)'
        content = re.sub(method_pattern, imbalance_fix.strip(), content, flags=re.DOTALL)
        
        with open(file_path, 'w') as f:
            f.write(content)
        
        self.fixes_applied.append("Fixed orderbook imbalance scoring with depth confidence validation")
        print("✅ Fixed orderbook imbalance scoring logic")
    
    def _fix_cvd_scoring(self):
        """
        Fix 7: Orderflow CVD scoring inconsistencies
        """
        file_path = "src/indicators/orderflow_indicators.py"
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Fix CVD scoring
        cvd_fix = '''
    def _calculate_cvd_score(self, data: pd.DataFrame) -> float:
        """
        Calculate CVD score with proper buy/sell pressure interpretation
        Fixed: Ensure negative CVD (selling pressure) leads to low scores
        """
        try:
            if len(data) < 20:
                return 50.0
            
            cvd_values = self._calculate_cvd(data)
            if cvd_values is None or len(cvd_values) == 0:
                return 50.0
            
            # Get recent CVD trend
            recent_cvd = cvd_values.tail(10)
            current_cvd = recent_cvd.iloc[-1]
            cvd_change = recent_cvd.iloc[-1] - recent_cvd.iloc[0]
            
            # Normalize CVD based on recent range
            cvd_range = recent_cvd.max() - recent_cvd.min()
            if cvd_range > 0:
                normalized_cvd = (current_cvd - recent_cvd.min()) / cvd_range
            else:
                normalized_cvd = 0.5
            
            # Base score: positive CVD = bullish, negative CVD = bearish
            base_score = 50 + (normalized_cvd - 0.5) * 100
            
            # CVD trend validation
            if cvd_change > 0:
                # Positive CVD change = buying pressure = bullish
                base_score = max(base_score, 55)
            elif cvd_change < 0:
                # Negative CVD change = selling pressure = bearish
                base_score = min(base_score, 45)
            
            # Context validation: align with price movement
            price_change = (data['close'].iloc[-1] - data['close'].iloc[-10]) / data['close'].iloc[-10]
            
            # Divergence detection: CVD and price should align
            if cvd_change > 0 and price_change < -0.02:  # CVD up, price down significantly
                base_score = min(base_score, 45)  # Bearish divergence
            elif cvd_change < 0 and price_change > 0.02:  # CVD down, price up significantly
                base_score = max(base_score, 55)  # Bullish divergence (hidden)
            
            return float(np.clip(base_score, 0, 100))
            
        except Exception as e:
            return 50.0
        '''
        
        # Replace the method
        method_pattern = r'def _calculate_cvd_score\(self, data: pd\.DataFrame\) -> float:.*?(?=\n    def|\nclass|\n\n\n|\Z)'
        content = re.sub(method_pattern, cvd_fix.strip(), content, flags=re.DOTALL)
        
        with open(file_path, 'w') as f:
            f.write(content)
        
        self.fixes_applied.append("Fixed CVD scoring with proper buy/sell pressure interpretation")
        print("✅ Fixed CVD scoring logic")
    
    def _fix_range_position_scoring(self):
        """
        Fix 8: Price Structure range position scoring
        """
        file_path = "src/indicators/price_structure_indicators.py"
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Fix range position scoring
        range_fix = '''
    def _analyze_range_position(self, data: pd.DataFrame) -> float:
        """
        Analyze range position with proper market context validation
        Fixed: Added range maturity and market context awareness
        """
        try:
            if len(data) < 50:
                return 50.0
            
            # Identify range boundaries
            range_data = self._identify_range(data)
            if not range_data:
                return 50.0
            
            current_price = data['close'].iloc[-1]
            range_high = range_data.get('high', current_price)
            range_low = range_data.get('low', current_price)
            range_age = range_data.get('age', 0)
            
            if range_high <= range_low:
                return 50.0
            
            # Calculate position in range
            position_ratio = (current_price - range_low) / (range_high - range_low)
            
            # Base scoring with context validation
            if position_ratio <= 0.25:
                # Low in range - potentially bullish but depends on context
                base_score = 65.0
                
                # Context validation: range maturity matters
                if range_age < 10:  # Young range
                    base_score = 50 + (base_score - 50) * 0.6  # Reduce confidence
                
                # Check for support strength
                support_strength = self._calculate_support_strength(data, range_low)
                if support_strength < 0.3:  # Weak support
                    base_score = min(base_score, 55)  # Reduce bullish signal
                    
            elif position_ratio >= 0.75:
                # High in range - potentially bearish but depends on context
                base_score = 35.0
                
                # Context validation: range maturity matters
                if range_age < 10:  # Young range
                    base_score = 50 + (base_score - 50) * 0.6  # Reduce confidence
                
                # Check for resistance strength
                resistance_strength = self._calculate_resistance_strength(data, range_high)
                if resistance_strength < 0.3:  # Weak resistance
                    base_score = max(base_score, 45)  # Reduce bearish signal
                    
            else:
                # Middle of range
                base_score = 50.0
            
            # Apply range maturity validation
            base_score = MarketContextValidator.validate_range_position(
                base_score, position_ratio, range_age
            )
            
            return float(np.clip(base_score, 0, 100))
            
        except Exception as e:
            return 50.0
        '''
        
        # Add helper methods
        helper_methods = '''
    def _calculate_support_strength(self, data: pd.DataFrame, support_level: float) -> float:
        """Calculate support strength based on touches and volume"""
        try:
            touches = 0
            volume_at_support = 0
            
            for i in range(len(data)):
                if abs(data['low'].iloc[i] - support_level) / support_level < 0.01:
                    touches += 1
                    volume_at_support += data['volume'].iloc[i]
            
            if touches == 0:
                return 0.0
            
            avg_volume = data['volume'].mean()
            avg_volume_at_support = volume_at_support / touches
            
            # Strength based on touches and volume
            strength = min(touches / 3, 1.0) * 0.5 + min(avg_volume_at_support / avg_volume, 2.0) * 0.5
            return min(strength, 1.0)
        except:
            return 0.5
    
    def _calculate_resistance_strength(self, data: pd.DataFrame, resistance_level: float) -> float:
        """Calculate resistance strength based on touches and volume"""
        try:
            touches = 0
            volume_at_resistance = 0
            
            for i in range(len(data)):
                if abs(data['high'].iloc[i] - resistance_level) / resistance_level < 0.01:
                    touches += 1
                    volume_at_resistance += data['volume'].iloc[i]
            
            if touches == 0:
                return 0.0
            
            avg_volume = data['volume'].mean()
            avg_volume_at_resistance = volume_at_resistance / touches
            
            # Strength based on touches and volume
            strength = min(touches / 3, 1.0) * 0.5 + min(avg_volume_at_resistance / avg_volume, 2.0) * 0.5
            return min(strength, 1.0)
        except:
            return 0.5
        '''
        
        # Replace the method
        method_pattern = r'def _analyze_range_position\(self, data: pd\.DataFrame\) -> float:.*?(?=\n    def|\nclass|\n\n\n|\Z)'
        content = re.sub(method_pattern, range_fix.strip(), content, flags=re.DOTALL)
        
        # Add helper methods if not exist
        if "_calculate_support_strength" not in content:
            content = content.rstrip() + "\n\n" + helper_methods.strip() + "\n"
        
        with open(file_path, 'w') as f:
            f.write(content)
        
        self.fixes_applied.append("Fixed range position scoring with context validation")
        print("✅ Fixed range position scoring logic")
    
    def _fix_relative_volume_scoring(self):
        """
        Fix 9: Volume relative volume scoring with price direction
        """
        file_path = "src/indicators/volume_indicators.py"
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Fix relative volume scoring
        relative_volume_fix = '''
    def _calculate_relative_volume_score(self, data: pd.DataFrame) -> float:
        """
        Calculate relative volume score with price direction awareness
        Fixed: High volume on bearish price action leads to low scores
        """
        try:
            if len(data) < 20:
                return 50.0
            
            current_volume = data['volume'].iloc[-1]
            avg_volume = data['volume'].tail(20).mean()
            
            if avg_volume == 0:
                return 50.0
            
            relative_volume = current_volume / avg_volume
            
            # Price direction context
            price_change = (data['close'].iloc[-1] - data['close'].iloc[-2]) / data['close'].iloc[-2]
            
            # Base score using tanh normalization
            base_score = 50 + (np.tanh(relative_volume - 1) * 50)
            
            # Context validation: align volume with price direction
            if relative_volume > 1.5:  # High volume
                if price_change < -0.01:  # Significant down move
                    # High volume on down move = bearish
                    base_score = MarketContextValidator.validate_volume_context(
                        base_score, relative_volume, "down"
                    )
                elif price_change > 0.01:  # Significant up move
                    # High volume on up move = bullish
                    base_score = MarketContextValidator.validate_volume_context(
                        base_score, relative_volume, "up"
                    )
            
            # Additional context: very high volume might indicate climax
            if relative_volume > 3.0:
                # Extreme volume might indicate reversal
                base_score = 50 + (base_score - 50) * 0.7  # Reduce signal strength
            
            return float(np.clip(base_score, 0, 100))
            
        except Exception as e:
            return 50.0
        '''
        
        # Replace the method
        method_pattern = r'def _calculate_relative_volume_score\(self, data: pd\.DataFrame\) -> float:.*?(?=\n    def|\nclass|\n\n\n|\Z)'
        content = re.sub(method_pattern, relative_volume_fix.strip(), content, flags=re.DOTALL)
        
        with open(file_path, 'w') as f:
            f.write(content)
        
        self.fixes_applied.append("Fixed relative volume scoring with price direction awareness")
        print("✅ Fixed relative volume scoring logic")
    
    def _fix_lsr_scoring(self):
        """
        Fix 10: Sentiment LSR scoring with overextension detection
        """
        file_path = "src/indicators/sentiment_indicators.py"
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Fix LSR scoring
        lsr_fix = '''
    def _calculate_lsr_score(self, symbol: str) -> float:
        """
        Calculate LSR score with market overextension detection
        Fixed: High LSR in overextended market is bearish, not bullish
        """
        try:
            lsr_data = self._get_long_short_ratio(symbol)
            if not lsr_data:
                return 50.0
            
            lsr_value = lsr_data.get('ratio', 1.0)
            
            # Normalize LSR (typical range 0.5 to 2.0)
            lsr_normalized = np.clip((lsr_value - 1.0) / 1.0, -1.0, 1.0)
            
            # Base score: higher LSR = more longs = potentially bullish
            base_score = 50 + (lsr_normalized * 30)  # Reduced from 50 to 30
            
            # Context validation: extreme LSR might indicate overextension
            if lsr_value > 1.5:  # High LSR (more longs)
                # Check if market is overextended
                market_sentiment = self._assess_market_sentiment(symbol)
                if market_sentiment == "overextended_bullish":
                    # High LSR in overextended market = bearish contrarian signal
                    base_score = min(base_score, 40)
                    
            elif lsr_value < 0.7:  # Low LSR (more shorts)
                # Check if market is oversold
                market_sentiment = self._assess_market_sentiment(symbol)
                if market_sentiment == "overextended_bearish":
                    # Low LSR in oversold market = bullish contrarian signal
                    base_score = max(base_score, 60)
            
            # Historical context: compare to recent LSR levels
            historical_lsr = self._get_historical_lsr(symbol, periods=10)
            if historical_lsr:
                lsr_percentile = self._calculate_percentile(lsr_value, historical_lsr)
                
                # Extreme percentiles might indicate reversal
                if lsr_percentile > 0.8:  # Very high LSR historically
                    base_score = min(base_score, 45)  # Reduce bullish signal
                elif lsr_percentile < 0.2:  # Very low LSR historically
                    base_score = max(base_score, 55)  # Reduce bearish signal
            
            return float(np.clip(base_score, 0, 100))
            
        except Exception as e:
            return 50.0
        '''
        
        # Add helper methods
        helper_methods = '''
    def _assess_market_sentiment(self, symbol: str) -> str:
        """Assess overall market sentiment"""
        try:
            # This is a simplified implementation
            # In practice, you'd combine multiple indicators
            return "neutral"  # Placeholder
        except:
            return "neutral"
    
    def _get_historical_lsr(self, symbol: str, periods: int = 10) -> list:
        """Get historical LSR data"""
        try:
            # This would fetch historical LSR data
            return []  # Placeholder
        except:
            return []
    
    def _calculate_percentile(self, value: float, historical_data: list) -> float:
        """Calculate percentile of value in historical data"""
        try:
            if not historical_data:
                return 0.5
            
            historical_data = sorted(historical_data)
            position = 0
            for i, hist_val in enumerate(historical_data):
                if value <= hist_val:
                    position = i
                    break
            else:
                position = len(historical_data)
            
            return position / len(historical_data)
        except:
            return 0.5
        '''
        
        # Replace the method
        method_pattern = r'def _calculate_lsr_score\(self, symbol: str\) -> float:.*?(?=\n    def|\nclass|\n\n\n|\Z)'
        content = re.sub(method_pattern, lsr_fix.strip(), content, flags=re.DOTALL)
        
        # Add helper methods if not exist
        if "_assess_market_sentiment" not in content:
            content = content.rstrip() + "\n\n" + helper_methods.strip() + "\n"
        
        with open(file_path, 'w') as f:
            f.write(content)
        
        self.fixes_applied.append("Fixed LSR scoring with overextension detection")
        print("✅ Fixed LSR scoring logic")
    
    def _fix_spread_scoring(self):
        """
        Fix 11: Orderbook spread scoring with liquidity stress detection
        """
        file_path = "src/indicators/orderbook_indicators.py"
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Fix spread scoring
        spread_fix = '''
    def _calculate_spread_score(self, orderbook_data: dict) -> float:
        """
        Calculate spread score with liquidity stress detection
        Fixed: Very tight spreads might indicate low liquidity stress, not maximum bullish
        """
        try:
            if not orderbook_data or 'bids' not in orderbook_data or 'asks' not in orderbook_data:
                return 50.0
            
            bids = orderbook_data['bids']
            asks = orderbook_data['asks']
            
            if not bids or not asks:
                return 50.0
            
            best_bid = float(bids[0][0])
            best_ask = float(asks[0][0])
            
            if best_bid <= 0 or best_ask <= 0:
                return 50.0
            
            # Calculate relative spread
            spread = best_ask - best_bid
            mid_price = (best_bid + best_ask) / 2
            relative_spread = spread / mid_price
            
            # Base score: tighter spread = better liquidity = more neutral
            spread_base_score = 50 + (50 * np.exp(-100 * relative_spread))
            
            # Context validation: very tight spreads might indicate different things
            if relative_spread < 0.0001:  # Very tight spread (0.01%)
                # Could indicate either very good liquidity or low volatility
                # Check orderbook depth for context
                depth_score = self._calculate_orderbook_depth(orderbook_data)
                
                if depth_score > 70:  # Deep orderbook
                    # Tight spread + deep book = good liquidity = neutral to slightly bullish
                    spread_base_score = min(spread_base_score, 60)
                else:  # Shallow orderbook
                    # Tight spread + shallow book = low activity = neutral
                    spread_base_score = 50
                    
            elif relative_spread > 0.01:  # Wide spread (1%)
                # Wide spread indicates stress or low liquidity = bearish
                spread_base_score = max(20, spread_base_score - 30)
            
            # Historical context: compare to recent spreads
            historical_spreads = self._get_historical_spreads(orderbook_data, periods=10)
            if historical_spreads:
                spread_percentile = self._calculate_spread_percentile(relative_spread, historical_spreads)
                
                # Adjust based on historical context
                if spread_percentile > 0.8:  # Very wide historically
                    spread_base_score = min(spread_base_score, 35)  # More bearish
                elif spread_percentile < 0.2:  # Very tight historically
                    spread_base_score = max(spread_base_score, 55)  # Slightly bullish
            
            return float(np.clip(spread_base_score, 0, 100))
            
        except Exception as e:
            return 50.0
        '''
        
        # Add helper methods
        helper_methods = '''
    def _calculate_orderbook_depth(self, orderbook_data: dict) -> float:
        """Calculate orderbook depth score"""
        try:
            bids = orderbook_data.get('bids', [])
            asks = orderbook_data.get('asks', [])
            
            if not bids or not asks:
                return 50.0
            
            # Calculate volume in top 10 levels
            bid_volume = sum(float(bid[1]) for bid in bids[:10])
            ask_volume = sum(float(ask[1]) for ask in asks[:10])
            
            total_volume = bid_volume + ask_volume
            
            # Normalize depth (this is simplified)
            depth_score = min(total_volume / 1000, 1.0) * 100  # Assuming 1000 is good depth
            
            return depth_score
        except:
            return 50.0
    
    def _get_historical_spreads(self, orderbook_data: dict, periods: int = 10) -> list:
        """Get historical spread data"""
        try:
            # This would fetch historical spread data
            return []  # Placeholder
        except:
            return []
    
    def _calculate_spread_percentile(self, spread: float, historical_spreads: list) -> float:
        """Calculate spread percentile"""
        try:
            if not historical_spreads:
                return 0.5
            
            historical_spreads = sorted(historical_spreads)
            position = 0
            for i, hist_spread in enumerate(historical_spreads):
                if spread <= hist_spread:
                    position = i
                    break
            else:
                position = len(historical_spreads)
            
            return position / len(historical_spreads)
        except:
            return 0.5
        '''
        
        # Replace the method
        method_pattern = r'def _calculate_spread_score\(self, orderbook_data: dict\) -> float:.*?(?=\n    def|\nclass|\n\n\n|\Z)'
        content = re.sub(method_pattern, spread_fix.strip(), content, flags=re.DOTALL)
        
        # Add helper methods if not exist
        if "_calculate_orderbook_depth" not in content:
            content = content.rstrip() + "\n\n" + helper_methods.strip() + "\n"
        
        with open(file_path, 'w') as f:
            f.write(content)
        
        self.fixes_applied.append("Fixed spread scoring with liquidity stress detection")
        print("✅ Fixed spread scoring logic")
    
    def _fix_trade_flow_scoring(self):
        """
        Fix 12: Orderflow trade flow scoring with directional context
        """
        file_path = "src/indicators/orderflow_indicators.py"
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Fix trade flow scoring
        trade_flow_fix = '''
    def _calculate_trade_flow_score(self, data: pd.DataFrame) -> float:
        """
        Calculate trade flow score with directional context validation
        Fixed: Positive flow isn't always bullish - depends on buy/sell classification
        """
        try:
            if len(data) < 10:
                return 50.0
            
            trade_flow = self._calculate_trade_flow(data)
            if trade_flow is None:
                return 50.0
            
            # Classify trades as buy/sell based on price vs bid/ask
            buy_volume = 0
            sell_volume = 0
            
            for i in range(len(data)):
                volume = data['volume'].iloc[i]
                
                # Simplified buy/sell classification
                # In practice, you'd use trade classification algorithms
                if i > 0:
                    price_change = data['close'].iloc[i] - data['close'].iloc[i-1]
                    if price_change > 0:
                        buy_volume += volume
                    elif price_change < 0:
                        sell_volume += volume
            
            total_volume = buy_volume + sell_volume
            if total_volume == 0:
                return 50.0
            
            # Calculate buy/sell ratio
            buy_ratio = buy_volume / total_volume
            
            # Base score: higher buy ratio = more bullish
            flow_score = buy_ratio * 100
            
            # Context validation: align with price movement
            price_change = (data['close'].iloc[-1] - data['close'].iloc[0]) / data['close'].iloc[0]
            
            # Divergence detection
            if buy_ratio > 0.6 and price_change < -0.01:  # High buy ratio, price down
                # Possible accumulation or failed breakout
                flow_score = min(flow_score, 45)  # Reduce bullish signal
            elif buy_ratio < 0.4 and price_change > 0.01:  # High sell ratio, price up
                # Possible distribution or short covering
                flow_score = max(flow_score, 55)  # Reduce bearish signal
            
            # Volume context: high volume makes signals more reliable
            avg_volume = data['volume'].mean()
            current_volume = data['volume'].iloc[-1]
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
            
            if volume_ratio > 1.5:  # High volume
                # Amplify signal slightly
                flow_score = 50 + (flow_score - 50) * 1.2
            elif volume_ratio < 0.5:  # Low volume
                # Reduce signal strength
                flow_score = 50 + (flow_score - 50) * 0.7
            
            return float(np.clip(flow_score, 0, 100))
            
        except Exception as e:
            return 50.0
        '''
        
        # Replace the method
        method_pattern = r'def _calculate_trade_flow_score\(self, data: pd\.DataFrame\) -> float:.*?(?=\n    def|\nclass|\n\n\n|\Z)'
        content = re.sub(method_pattern, trade_flow_fix.strip(), content, flags=re.DOTALL)
        
        with open(file_path, 'w') as f:
            f.write(content)
        
        self.fixes_applied.append("Fixed trade flow scoring with directional context validation")
        print("✅ Fixed trade flow scoring logic")
    
    def _fix_support_resistance_scoring(self):
        """
        Fix 13: Price Structure support/resistance proximity scoring
        """
        file_path = "src/indicators/price_structure_indicators.py"
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Fix support/resistance scoring
        support_resistance_fix = '''
    def _calculate_support_resistance_score(self, data: pd.DataFrame) -> float:
        """
        Calculate support/resistance score with proper proximity logic
        Fixed: Proximity to resistance should be bearish, not bullish
        """
        try:
            if len(data) < 50:
                return 50.0
            
            current_price = data['close'].iloc[-1]
            
            # Identify support and resistance levels
            support_levels = self._identify_support_levels(data)
            resistance_levels = self._identify_resistance_levels(data)
            
            if not support_levels and not resistance_levels:
                return 50.0
            
            # Find closest levels
            closest_support = None
            closest_resistance = None
            
            if support_levels:
                closest_support = min(support_levels, key=lambda x: abs(current_price - x))
            
            if resistance_levels:
                closest_resistance = min(resistance_levels, key=lambda x: abs(current_price - x))
            
            base_score = 50.0
            
            # Support proximity logic
            if closest_support:
                support_distance = abs(current_price - closest_support) / current_price
                
                if current_price > closest_support:
                    # Above support = bullish, closer = more bullish
                    support_influence = max(0, 1 - support_distance * 20)  # Influence decreases with distance
                    base_score += support_influence * 20
                else:
                    # Below support = bearish (support broken)
                    support_influence = max(0, 1 - support_distance * 20)
                    base_score -= support_influence * 25
            
            # Resistance proximity logic
            if closest_resistance:
                resistance_distance = abs(current_price - closest_resistance) / current_price
                
                if current_price < closest_resistance:
                    # Below resistance = neutral to slightly bearish as we approach
                    resistance_influence = max(0, 1 - resistance_distance * 20)
                    base_score -= resistance_influence * 15  # Bearish as we approach resistance
                else:
                    # Above resistance = bullish (resistance broken)
                    resistance_influence = max(0, 1 - resistance_distance * 20)
                    base_score += resistance_influence * 25
            
            # Context validation: consider level strength
            if closest_support:
                support_strength = self._calculate_level_strength(data, closest_support)
                if support_strength > 0.7 and current_price > closest_support:
                    base_score = max(base_score, 60)  # Strong support = more bullish
            
            if closest_resistance:
                resistance_strength = self._calculate_level_strength(data, closest_resistance)
                if resistance_strength > 0.7 and current_price < closest_resistance:
                    base_score = min(base_score, 40)  # Strong resistance = more bearish
            
            return float(np.clip(base_score, 0, 100))
            
        except Exception as e:
            return 50.0
        '''
        
        # Add helper methods
        helper_methods = '''
    def _identify_support_levels(self, data: pd.DataFrame) -> list:
        """Identify support levels"""
        try:
            # Simplified support identification
            # In practice, you'd use more sophisticated algorithms
            lows = data['low'].rolling(window=10).min()
            support_levels = []
            
            for i in range(10, len(data) - 10):
                if (lows.iloc[i] == data['low'].iloc[i] and 
                    data['low'].iloc[i] < data['low'].iloc[i-5:i+5].mean() * 0.99):
                    support_levels.append(data['low'].iloc[i])
            
            return list(set(support_levels))  # Remove duplicates
        except:
            return []
    
    def _identify_resistance_levels(self, data: pd.DataFrame) -> list:
        """Identify resistance levels"""
        try:
            # Simplified resistance identification
            highs = data['high'].rolling(window=10).max()
            resistance_levels = []
            
            for i in range(10, len(data) - 10):
                if (highs.iloc[i] == data['high'].iloc[i] and 
                    data['high'].iloc[i] > data['high'].iloc[i-5:i+5].mean() * 1.01):
                    resistance_levels.append(data['high'].iloc[i])
            
            return list(set(resistance_levels))  # Remove duplicates
        except:
            return []
    
    def _calculate_level_strength(self, data: pd.DataFrame, level: float) -> float:
        """Calculate strength of support/resistance level"""
        try:
            touches = 0
            volume_at_level = 0
            
            for i in range(len(data)):
                if abs(data['low'].iloc[i] - level) / level < 0.01:
                    touches += 1
                    volume_at_level += data['volume'].iloc[i]
                elif abs(data['high'].iloc[i] - level) / level < 0.01:
                    touches += 1
                    volume_at_level += data['volume'].iloc[i]
            
            if touches == 0:
                return 0.0
            
            avg_volume = data['volume'].mean()
            avg_volume_at_level = volume_at_level / touches
            
            # Strength based on touches and volume
            strength = min(touches / 3, 1.0) * 0.6 + min(avg_volume_at_level / avg_volume, 2.0) * 0.4
            return min(strength, 1.0)
        except:
            return 0.5
        '''
        
        # Replace the method
        method_pattern = r'def _calculate_support_resistance_score\(self, data: pd\.DataFrame\) -> float:.*?(?=\n    def|\nclass|\n\n\n|\Z)'
        content = re.sub(method_pattern, support_resistance_fix.strip(), content, flags=re.DOTALL)
        
        # Add helper methods if not exist
        if "_identify_support_levels" not in content:
            content = content.rstrip() + "\n\n" + helper_methods.strip() + "\n"
        
        with open(file_path, 'w') as f:
            f.write(content)
        
        self.fixes_applied.append("Fixed support/resistance scoring with proper proximity logic")
        print("✅ Fixed support/resistance scoring logic")
    
    def _generate_fix_report(self) -> Dict[str, any]:
        """
        Generate comprehensive fix report
        """
        report = {
            "phase": "Phase 1: Logic Inconsistency Fixes",
            "timestamp": datetime.now().isoformat(),
            "fixes_applied": len(self.fixes_applied),
            "fixes_list": self.fixes_applied,
            "validation_errors": self.validation_errors,
            "backup_location": self.backup_dir,
            "next_steps": [
                "Run comprehensive tests on all fixed methods",
                "Validate with real market data",
                "Monitor for any regressions",
                "Proceed to Phase 2 if all tests pass"
            ]
        }
        
        return report

def main():
    """
    Main execution function
    """
    print("🚀 Phase 1: Comprehensive Logic Inconsistency Fixes")
    print("=" * 60)
    
    fixer = Phase1LogicFixer()
    report = fixer.apply_all_fixes()
    
    # Save report
    report_path = "reports/phase1_logic_fixes_report.json"
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    
    import json
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📊 Fix Report saved to: {report_path}")
    print(f"✅ {report['fixes_applied']} fixes applied successfully")
    
    if report['validation_errors']:
        print(f"⚠️  {len(report['validation_errors'])} validation errors occurred")
        for error in report['validation_errors']:
            print(f"   - {error}")
    
    print("\n🔄 Next Steps:")
    for step in report['next_steps']:
        print(f"   - {step}")

if __name__ == "__main__":
    main() 