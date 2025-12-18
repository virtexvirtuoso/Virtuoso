/**
 * Validation Script for Signal Report URL Construction
 * Tests the formatTimestampForFile() and openSignalReport() logic with edge cases
 *
 * Run with: node scripts/validate_signal_report_url_logic.js
 */

// Replicate the formatTimestampForFile function
function formatTimestampForFile(timestamp) {
    if (!timestamp) return '';
    const date = new Date(timestamp);

    // Use UTC to match server-side Python report generation
    const year = date.getUTCFullYear();
    const month = String(date.getUTCMonth() + 1).padStart(2, '0');
    const day = String(date.getUTCDate()).padStart(2, '0');
    const hours = String(date.getUTCHours()).padStart(2, '0');
    const minutes = String(date.getUTCMinutes()).padStart(2, '0');
    const seconds = String(date.getUTCSeconds()).padStart(2, '0');

    return `${year}${month}${day}_${hours}${minutes}${seconds}`;
}

// Replicate the openSignalReport function (just URL construction)
function constructReportUrl(signal) {
    if (!signal || !signal.timestamp) {
        return { error: 'missing signal data or timestamp', signal };
    }

    // Format symbol (add back USDT if not present)
    const symbol = signal.symbol.toLowerCase().includes('usdt')
        ? signal.symbol.toLowerCase()
        : signal.symbol.toLowerCase() + 'usdt';

    // Format score as XXpX (e.g., 72 -> 72p0, 56.9 -> 56p9)
    // Use .toFixed(1) to match Python report generator and avoid rounding overflow
    const scoreStr = signal.score.toFixed(1).replace('.', 'p');

    // Format timestamp
    const timestampStr = formatTimestampForFile(signal.timestamp);

    // Construct filename
    const filename = `${symbol}_${signal.direction}_${scoreStr}_${timestampStr}.html`;
    const reportUrl = `/reports/html/${filename}`;

    return { url: reportUrl, filename };
}

// Test cases
const testCases = [
    // Normal cases
    {
        name: 'Standard BTC long signal',
        signal: { symbol: 'BTC', direction: 'LONG', score: 72.5, timestamp: 1701561876000 },
        expected: { symbol: 'btcusdt', direction: 'LONG', score: '72p5', timestamp: '20231203_004436' }
    },
    {
        name: 'Standard ETH short signal',
        signal: { symbol: 'ETH', direction: 'SHORT', score: 32.8, timestamp: 1698661505000 },
        expected: { symbol: 'ethusdt', direction: 'SHORT', score: '32p8', timestamp: '20231030_102505' }
    },

    // Score edge cases
    {
        name: 'Integer score (72.0)',
        signal: { symbol: 'BTC', direction: 'LONG', score: 72, timestamp: 1701561876000 },
        expected: { symbol: 'btcusdt', direction: 'LONG', score: '72p0', timestamp: '20231203_004436' }
    },
    {
        name: 'High precision decimal (56.87 rounds to 56.9)',
        signal: { symbol: 'BTC', direction: 'LONG', score: 56.87, timestamp: 1701561876000 },
        expected: { symbol: 'btcusdt', direction: 'LONG', score: '56p9', timestamp: '20231203_004436' }
    },
    {
        name: 'Low precision decimal (56.12 rounds to 56.1)',
        signal: { symbol: 'BTC', direction: 'LONG', score: 56.12, timestamp: 1701561876000 },
        expected: { symbol: 'btcusdt', direction: 'LONG', score: '56p1', timestamp: '20231203_004436' }
    },
    {
        name: 'Edge decimal (69.95 rounds to 70.0)',
        signal: { symbol: 'BTC', direction: 'LONG', score: 69.95, timestamp: 1701561876000 },
        expected: { symbol: 'btcusdt', direction: 'LONG', score: '70p0', timestamp: '20231203_004436' }
    },
    {
        name: 'Very low score (12.3)',
        signal: { symbol: 'BTC', direction: 'SHORT', score: 12.3, timestamp: 1701561876000 },
        expected: { symbol: 'btcusdt', direction: 'SHORT', score: '12p3', timestamp: '20231203_004436' }
    },
    {
        name: 'Very high score (98.7)',
        signal: { symbol: 'BTC', direction: 'LONG', score: 98.7, timestamp: 1701561876000 },
        expected: { symbol: 'btcusdt', direction: 'LONG', score: '98p7', timestamp: '20231203_004436' }
    },

    // Symbol edge cases
    {
        name: 'Symbol without USDT',
        signal: { symbol: 'BTC', direction: 'LONG', score: 70, timestamp: 1701561876000 },
        expected: { symbol: 'btcusdt', direction: 'LONG', score: '70p0', timestamp: '20231203_004436' }
    },
    {
        name: 'Symbol with USDT already',
        signal: { symbol: 'BTCUSDT', direction: 'LONG', score: 70, timestamp: 1701561876000 },
        expected: { symbol: 'btcusdt', direction: 'LONG', score: '70p0', timestamp: '20231203_004436' }
    },
    {
        name: 'Mixed case symbol',
        signal: { symbol: 'BtcUSDT', direction: 'LONG', score: 70, timestamp: 1701561876000 },
        expected: { symbol: 'btcusdt', direction: 'LONG', score: '70p0', timestamp: '20231203_004436' }
    },
    {
        name: 'Other altcoin (SOL)',
        signal: { symbol: 'SOL', direction: 'LONG', score: 65.4, timestamp: 1701561876000 },
        expected: { symbol: 'solusdt', direction: 'LONG', score: '65p4', timestamp: '20231203_004436' }
    },

    // Timestamp edge cases
    {
        name: 'Unix timestamp in seconds (old format)',
        signal: { symbol: 'BTC', direction: 'LONG', score: 70, timestamp: 1701561876 },
        expected: { symbol: 'btcusdt', direction: 'LONG', score: '70p0', timestamp: '19700120_143936' }
    },
    {
        name: 'Recent timestamp (Dec 11, 2025)',
        signal: { symbol: 'BTC', direction: 'LONG', score: 70, timestamp: 1733933400000 },
        expected: { symbol: 'btcusdt', direction: 'LONG', score: '70p0', timestamp: '20251211_120000' }
    },

    // Edge cases with zeros
    {
        name: 'Midnight timestamp',
        signal: { symbol: 'BTC', direction: 'LONG', score: 70, timestamp: 1701475200000 },
        expected: { symbol: 'btcusdt', direction: 'LONG', score: '70p0', timestamp: '20231202_000000' }
    },
    {
        name: 'Single digit day/month',
        signal: { symbol: 'BTC', direction: 'LONG', score: 70, timestamp: 1704067200000 },
        expected: { symbol: 'btcusdt', direction: 'LONG', score: '70p0', timestamp: '20240101_000000' }
    },

    // Missing data edge cases
    {
        name: 'Missing timestamp',
        signal: { symbol: 'BTC', direction: 'LONG', score: 70 },
        expected: { error: true }
    },
    {
        name: 'Null signal',
        signal: null,
        expected: { error: true }
    }
];

// Run tests
console.log('='.repeat(80));
console.log('Signal Report URL Construction Validation');
console.log('='.repeat(80));
console.log('');

let passed = 0;
let failed = 0;
const failures = [];

testCases.forEach((test, index) => {
    console.log(`Test ${index + 1}: ${test.name}`);
    console.log(`  Input: ${JSON.stringify(test.signal)}`);

    const result = constructReportUrl(test.signal);

    if (test.expected.error) {
        if (result.error) {
            console.log(`  ✅ PASS - Correctly handled error case`);
            passed++;
        } else {
            console.log(`  ❌ FAIL - Expected error but got: ${result.url}`);
            failed++;
            failures.push({ test: test.name, reason: 'Expected error but got success' });
        }
    } else {
        // Parse the URL to validate components
        const filename = result.filename;
        const parts = filename.replace('.html', '').split('_');
        const symbol = parts[0];
        const direction = parts[1];
        const score = parts[2];
        const timestamp = `${parts[3]}_${parts[4]}`;

        const symbolMatch = symbol === test.expected.symbol;
        const directionMatch = direction === test.expected.direction;
        const scoreMatch = score === test.expected.score;
        const timestampMatch = timestamp === test.expected.timestamp;

        if (symbolMatch && directionMatch && scoreMatch && timestampMatch) {
            console.log(`  ✅ PASS`);
            console.log(`  Generated: ${result.url}`);
            passed++;
        } else {
            console.log(`  ❌ FAIL`);
            console.log(`  Expected: /reports/html/${test.expected.symbol}_${test.expected.direction}_${test.expected.score}_${test.expected.timestamp}.html`);
            console.log(`  Got:      ${result.url}`);
            if (!symbolMatch) console.log(`    - Symbol mismatch: expected ${test.expected.symbol}, got ${symbol}`);
            if (!directionMatch) console.log(`    - Direction mismatch: expected ${test.expected.direction}, got ${direction}`);
            if (!scoreMatch) console.log(`    - Score mismatch: expected ${test.expected.score}, got ${score}`);
            if (!timestampMatch) console.log(`    - Timestamp mismatch: expected ${test.expected.timestamp}, got ${timestamp}`);
            failed++;
            failures.push({ test: test.name, expected: test.expected, got: { symbol, direction, score, timestamp } });
        }
    }
    console.log('');
});

console.log('='.repeat(80));
console.log('SUMMARY');
console.log('='.repeat(80));
console.log(`Total tests: ${testCases.length}`);
console.log(`Passed: ${passed} ✅`);
console.log(`Failed: ${failed} ❌`);
console.log(`Success rate: ${((passed / testCases.length) * 100).toFixed(1)}%`);

if (failures.length > 0) {
    console.log('');
    console.log('FAILED TESTS:');
    failures.forEach(f => {
        console.log(`  - ${f.test}`);
        if (f.reason) console.log(`    ${f.reason}`);
    });
    process.exit(1);
} else {
    console.log('');
    console.log('✅ All tests passed!');
    process.exit(0);
}
