#!/bin/bash
# 48-Hour Alert Enhancement Monitoring Script
# Monitors alert formatter performance and catches errors

MONITORING_START=$(date +%s)
MONITORING_END=$((MONITORING_START + 172800))  # 48 hours = 172800 seconds
LOG_FILE="logs/alert_enhancement_monitoring_$(date +%Y%m%d_%H%M%S).log"
VPS_HOST="${VPS_HOST:-vps}"

mkdir -p logs

echo "╔══════════════════════════════════════════════════════════════╗" | tee -a "$LOG_FILE"
echo "║     48-HOUR ALERT ENHANCEMENT PRODUCTION MONITORING          ║" | tee -a "$LOG_FILE"
echo "╚══════════════════════════════════════════════════════════════╝" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
echo "Start Time: $(date)" | tee -a "$LOG_FILE"
echo "End Time:   $(date -d @$MONITORING_END 2>/dev/null || date -r $MONITORING_END)" | tee -a "$LOG_FILE"
echo "Duration:   48 hours" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Monitoring metrics
TOTAL_CHECKS=0
ERRORS_DETECTED=0
NONE_ERRORS=0
PERFORMANCE_ISSUES=0

monitor_vps_logs() {
    echo "" | tee -a "$LOG_FILE"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a "$LOG_FILE"
    echo "🔍 Check #$TOTAL_CHECKS - $(date)" | tee -a "$LOG_FILE"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a "$LOG_FILE"

    # Check for None-related errors
    NONE_ERROR_COUNT=$(ssh "$VPS_HOST" "tail -1000 /home/linuxuser/trading/Virtuoso_ccxt/logs/main.log 2>/dev/null | grep -c \"NoneType.*alert_formatter\" || echo 0" | tr -d '\n\r')
    NONE_ERROR_COUNT=${NONE_ERROR_COUNT:-0}
    if [ "$NONE_ERROR_COUNT" -gt 0 ] 2>/dev/null; then
        echo "⚠️  WARNING: $NONE_ERROR_COUNT None-type errors detected!" | tee -a "$LOG_FILE"
        ERRORS_DETECTED=$((ERRORS_DETECTED + 1))
        NONE_ERRORS=$((NONE_ERRORS + NONE_ERROR_COUNT))

        # Get sample error
        echo "Sample error:" | tee -a "$LOG_FILE"
        ssh "$VPS_HOST" "tail -1000 /home/linuxuser/trading/Virtuoso_ccxt/logs/main.log 2>/dev/null | grep \"NoneType.*alert_formatter\" | tail -1" | tee -a "$LOG_FILE"
    else
        echo "✅ No None-type errors" | tee -a "$LOG_FILE"
    fi

    # Check alert generation rate
    ALERT_COUNT=$(ssh "$VPS_HOST" "tail -1000 /home/linuxuser/trading/Virtuoso_ccxt/logs/main.log 2>/dev/null | grep -c \"format_.*_alert\" || echo 0" | tr -d '\n\r')
    ALERT_COUNT=${ALERT_COUNT:-0}
    echo "📊 Alerts generated: $ALERT_COUNT (last 1000 lines)" | tee -a "$LOG_FILE"

    # Check for performance issues
    SLOW_ALERTS=$(ssh "$VPS_HOST" "tail -1000 /home/linuxuser/trading/Virtuoso_ccxt/logs/main.log 2>/dev/null | grep -c \"alert.*slow\" || echo 0" | tr -d '\n\r')
    SLOW_ALERTS=${SLOW_ALERTS:-0}
    if [ "$SLOW_ALERTS" -gt 0 ] 2>/dev/null; then
        echo "⚠️  WARNING: $SLOW_ALERTS slow alert warnings!" | tee -a "$LOG_FILE"
        PERFORMANCE_ISSUES=$((PERFORMANCE_ISSUES + SLOW_ALERTS))
    fi

    # Check service health
    MAIN_RUNNING=$(ssh "$VPS_HOST" "pgrep -f 'python.*main.py' | wc -l")
    WEB_RUNNING=$(ssh "$VPS_HOST" "pgrep -f 'python.*web_server.py' | wc -l")

    if [ "$MAIN_RUNNING" -eq 0 ]; then
        echo "🔴 CRITICAL: Main service is DOWN!" | tee -a "$LOG_FILE"
        ERRORS_DETECTED=$((ERRORS_DETECTED + 10))
    else
        echo "✅ Main service: RUNNING ($MAIN_RUNNING process)" | tee -a "$LOG_FILE"
    fi

    if [ "$WEB_RUNNING" -eq 0 ]; then
        echo "🔴 CRITICAL: Web service is DOWN!" | tee -a "$LOG_FILE"
        ERRORS_DETECTED=$((ERRORS_DETECTED + 10))
    else
        echo "✅ Web service: RUNNING ($WEB_RUNNING process)" | tee -a "$LOG_FILE"
    fi

    # Summary
    echo "" | tee -a "$LOG_FILE"
    echo "📈 Cumulative Stats:" | tee -a "$LOG_FILE"
    echo "  Total Checks:        $TOTAL_CHECKS" | tee -a "$LOG_FILE"
    echo "  Errors Detected:     $ERRORS_DETECTED" | tee -a "$LOG_FILE"
    echo "  None-type Errors:    $NONE_ERRORS" | tee -a "$LOG_FILE"
    echo "  Performance Issues:  $PERFORMANCE_ISSUES" | tee -a "$LOG_FILE"
}

# Main monitoring loop
echo "🚀 Starting 48-hour monitoring..." | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

while [ $(date +%s) -lt $MONITORING_END ]; do
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

    monitor_vps_logs

    # Check every 30 minutes
    REMAINING=$((MONITORING_END - $(date +%s)))
    HOURS_REMAINING=$((REMAINING / 3600))
    MINS_REMAINING=$(((REMAINING % 3600) / 60))

    echo "" | tee -a "$LOG_FILE"
    echo "⏰ Time remaining: ${HOURS_REMAINING}h ${MINS_REMAINING}m" | tee -a "$LOG_FILE"
    echo "💤 Next check in 30 minutes..." | tee -a "$LOG_FILE"
    echo "" | tee -a "$LOG_FILE"

    # Break if monitoring period ended
    if [ $REMAINING -le 0 ]; then
        break
    fi

    # Sleep 30 minutes, or remaining time if less than 30 minutes
    SLEEP_TIME=$((REMAINING < 1800 ? REMAINING : 1800))
    sleep $SLEEP_TIME
done

# Final summary
echo "" | tee -a "$LOG_FILE"
echo "╔══════════════════════════════════════════════════════════════╗" | tee -a "$LOG_FILE"
echo "║              48-HOUR MONITORING COMPLETE                     ║" | tee -a "$LOG_FILE"
echo "╚══════════════════════════════════════════════════════════════╝" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
echo "End Time: $(date)" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
echo "📊 FINAL STATISTICS:" | tee -a "$LOG_FILE"
echo "  Total Checks:        $TOTAL_CHECKS" | tee -a "$LOG_FILE"
echo "  Errors Detected:     $ERRORS_DETECTED" | tee -a "$LOG_FILE"
echo "  None-type Errors:    $NONE_ERRORS" | tee -a "$LOG_FILE"
echo "  Performance Issues:  $PERFORMANCE_ISSUES" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

if [ $ERRORS_DETECTED -eq 0 ] && [ $NONE_ERRORS -eq 0 ]; then
    echo "✅ SUCCESS: No errors detected during 48-hour monitoring period!" | tee -a "$LOG_FILE"
    EXIT_CODE=0
elif [ $NONE_ERRORS -gt 0 ]; then
    echo "⚠️  WARNING: None-type errors detected! Review required." | tee -a "$LOG_FILE"
    EXIT_CODE=1
else
    echo "🔴 CRITICAL: System errors detected! Immediate action required." | tee -a "$LOG_FILE"
    EXIT_CODE=2
fi

echo "" | tee -a "$LOG_FILE"
echo "Log file: $LOG_FILE" | tee -a "$LOG_FILE"

exit $EXIT_CODE
