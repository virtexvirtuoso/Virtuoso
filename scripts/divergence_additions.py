def _apply_divergence_bonuses(self, component_scores: Dict[str, float], divergences: Dict[str, Dict[str, Any]]) -> Dict[str, float]:
    """
    Apply divergence bonuses to component scores with detailed logging.
    
    Args:
        component_scores: Dictionary of component scores
        divergences: Dictionary of divergence information
        
    Returns:
        Dictionary of adjusted component scores
    """
    if not divergences:
        return component_scores
        
    # Make a copy to avoid modifying the original
    adjusted_scores = component_scores.copy()
    
    indicator_name = self.__class__.__name__.replace('Indicators', '')
    self.logger.info(f"\n=== Applying {indicator_name} Indicator Divergence Bonuses ===")
    self.logger.info(f"Original component scores:")
    for component, score in component_scores.items():
        self.logger.info(f"  - {component}: {score:.2f}")
        
    # Track total adjustments per component
    adjustments = {component: 0.0 for component in component_scores}
    
    # Apply bonuses from divergences
    for key, div_info in divergences.items():
        component = div_info.get('component')
        
        if component not in adjusted_scores:
            continue
            
        # Get bonus information
        bonus = div_info.get('bonus', 0.0)
        if 'bonus' not in div_info:
            # Calculate bonus based on divergence strength and type
            strength = div_info.get('strength', 0)
            div_type = div_info.get('type', 'neutral')
            
            # Bullish divergence increases score, bearish decreases
            bonus = strength * 0.1 * (1 if div_type == 'bullish' else -1)
            
            # Store bonus in divergence info for logging
            div_info['bonus'] = bonus
            
        if bonus == 0.0:
            continue
            
        # Get timeframe information if available
        tf1, tf2 = div_info.get('timeframes', ['', ''])
        if tf1 and tf2:
            tf1_friendly = self.TIMEFRAME_CONFIG.get(tf1, {}).get('friendly_name', tf1.upper())
            tf2_friendly = self.TIMEFRAME_CONFIG.get(tf2, {}).get('friendly_name', tf2.upper())
            timeframe_info = f"between {tf1_friendly} and {tf2_friendly}"
        else:
            timeframe_info = "in analysis"
        
        div_type = div_info.get('type', 'neutral')
        
        # Log the adjustment
        self.logger.info(f"  Adjusting {component} by {bonus:.2f} points ({div_type} divergence {timeframe_info})")
        
        # Update the score
        old_score = adjusted_scores[component]
        adjusted_scores[component] = np.clip(old_score + bonus, 0, 100)
        
        # Track total adjustment
        adjustments[component] += bonus
    
    # Store the adjustments for later use in the log_indicator_results method
    self._divergence_adjustments = adjustments
    
    # Log summary of adjustments
    self.logger.info("\nFinal adjusted scores:")
    for component, score in adjusted_scores.items():
        original = component_scores[component]
        adjustment = adjustments[component]
        
        if adjustment != 0:
            direction = "+" if adjustment > 0 else ""
            self.logger.info(f"  - {component}: {original:.2f} → {score:.2f} ({direction}{adjustment:.2f})")
        else:
            self.logger.info(f"  - {component}: {score:.2f} (unchanged)")
            
    return adjusted_scores

def log_indicator_results(self, final_score: float, component_scores: Dict[str, float], symbol: str = "") -> None:
    """
    Log indicator results with divergence adjustment information.
    
    This overrides the base method to include information about divergence adjustments
    in the score contribution breakdown.
    
    Args:
        final_score: Final calculated score
        component_scores: Dictionary of component scores
        symbol: Optional symbol to include in the title
    """
    # Handle component mapping for OrderflowIndicators
    if hasattr(self, 'component_mapping'):
        try:
            # Map component names for consistent logging
            mapped_scores = {}
            for component, score in component_scores.items():
                config_component = self.component_mapping.get(component, component)
                mapped_scores[config_component] = score
            component_scores = mapped_scores
        except Exception as e:
            self.logger.error(f"Error mapping components: {str(e)}")
    
    # Get the indicator name (remove "Indicators" suffix)
    indicator_name = self.__class__.__name__.replace('Indicators', '')
    
    # First check if we have divergence adjustment data
    divergence_adjustments = {}
    
    # See if we have the adjustments stored
    if hasattr(self, '_divergence_adjustments'):
        divergence_adjustments = self._divergence_adjustments
        
        # If using component mapping, map the adjustment keys too
        if hasattr(self, 'component_mapping'):
            try:
                mapped_adjustments = {}
                for component, adjustment in divergence_adjustments.items():
                    config_component = self.component_mapping.get(component, component)
                    mapped_adjustments[config_component] = adjustment
                divergence_adjustments = mapped_adjustments
            except Exception as e:
                self.logger.error(f"Error mapping divergence adjustments: {str(e)}")
    
    # First log the component breakdown with divergence adjustments
    breakdown_title = f"{indicator_name} Score Contribution Breakdown"
    
    # Create list of (component, score, weight, contribution) tuples
    contributions = []
    for component, score in component_scores.items():
        weight = self.component_weights.get(component, 0)
        contribution = score * weight
        contributions.append((component, score, weight, contribution))
    
    # Sort by contribution (highest first)
    contributions.sort(key=lambda x: x[3], reverse=True)
    
    # Use enhanced formatter with divergence adjustments
    from src.core.formatting.formatter import LogFormatter
    formatted_section = LogFormatter.format_score_contribution_section(
        breakdown_title, 
        contributions, 
        symbol,
        divergence_adjustments
    )
    self.logger.info(formatted_section)
    
    # Then log the final score
    from src.core.analysis.indicator_utils import log_final_score
    log_final_score(self.logger, indicator_name, final_score, symbol)
