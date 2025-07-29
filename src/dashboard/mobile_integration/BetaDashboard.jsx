import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  ActivityIndicator,
  RefreshControl,
  Dimensions
} from 'react-native';
import {
  LineChart,
  PieChart,
  ContributionGraph
} from 'react-native-chart-kit';

const API_BASE = 'http://45.77.40.77:8003/api/dashboard';
const screenWidth = Dimensions.get('window').width;

const BetaDashboard = () => {
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadBetaData();
  }, []);

  const loadBetaData = async () => {
    try {
      const response = await fetch(`${API_BASE}/mobile/beta-dashboard`);
      const jsonData = await response.json();
      
      if (jsonData.status === 'success') {
        setData(jsonData);
        setError(null);
      } else {
        setError('Failed to load beta analysis');
      }
    } catch (err) {
      setError('Network error: ' + err.message);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const onRefresh = () => {
    setRefreshing(true);
    loadBetaData();
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#ffbf00" />
        <Text style={styles.loadingText}>Loading Beta Analysis...</Text>
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.errorContainer}>
        <Text style={styles.errorText}>{error}</Text>
      </View>
    );
  }

  // Prepare chart data
  const prepareTimeSeriesData = () => {
    if (!data?.charts?.time_series?.data) return null;
    
    const firstSymbol = Object.keys(data.charts.time_series.data)[0];
    const points = data.charts.time_series.data[firstSymbol];
    
    return {
      labels: points.map(p => p.date.split('-')[2]), // Day only
      datasets: Object.keys(data.charts.time_series.data).map(symbol => ({
        data: data.charts.time_series.data[symbol].map(p => p.beta),
        color: (opacity = 1) => `rgba(255, 191, 0, ${opacity})`,
        strokeWidth: 2
      }))
    };
  };

  const preparePieData = () => {
    if (!data?.charts?.risk_distribution?.data) return [];
    
    return data.charts.risk_distribution.data.map(item => ({
      name: item.category.split(' ')[0], // Short name
      population: item.percentage,
      color: item.color,
      legendFontColor: '#ffbf00',
      legendFontSize: 12
    }));
  };

  const chartConfig = {
    backgroundColor: '#0c1a2b',
    backgroundGradientFrom: '#0f172a',
    backgroundGradientTo: '#0c1a2b',
    decimalPlaces: 2,
    color: (opacity = 1) => `rgba(255, 191, 0, ${opacity})`,
    labelColor: (opacity = 1) => `rgba(255, 191, 0, ${opacity})`,
    style: {
      borderRadius: 16
    },
    propsForDots: {
      r: '4',
      strokeWidth: '2',
      stroke: '#ff9900'
    }
  };

  return (
    <ScrollView
      style={styles.container}
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={onRefresh}
          tintColor="#ffbf00"
        />
      }
    >
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.title}>Bitcoin Beta Analysis</Text>
        <Text style={styles.subtitle}>7-Day Risk Analysis</Text>
      </View>

      {/* Overview Metrics */}
      <View style={styles.metricsContainer}>
        <View style={styles.metricCard}>
          <Text style={styles.metricValue}>
            {data.overview.market_beta.toFixed(2)}
          </Text>
          <Text style={styles.metricLabel}>Market Beta</Text>
        </View>
        <View style={styles.metricCard}>
          <Text style={styles.metricValue}>
            {data.overview.btc_dominance}%
          </Text>
          <Text style={styles.metricLabel}>BTC Dom</Text>
        </View>
        <View style={styles.metricCard}>
          <Text style={styles.metricValue}>
            {data.overview.avg_portfolio_beta.toFixed(2)}
          </Text>
          <Text style={styles.metricLabel}>Avg Beta</Text>
        </View>
        <View style={styles.metricCard}>
          <Text style={styles.metricValue}>
            {data.overview.total_assets}
          </Text>
          <Text style={styles.metricLabel}>Assets</Text>
        </View>
      </View>

      {/* Time Series Chart */}
      {prepareTimeSeriesData() && (
        <View style={styles.chartSection}>
          <Text style={styles.chartTitle}>Beta Trend (7 Days)</Text>
          <LineChart
            data={prepareTimeSeriesData()}
            width={screenWidth - 32}
            height={220}
            chartConfig={chartConfig}
            bezier
            style={styles.chart}
          />
        </View>
      )}

      {/* Risk Distribution */}
      <View style={styles.chartSection}>
        <Text style={styles.chartTitle}>Risk Distribution</Text>
        <PieChart
          data={preparePieData()}
          width={screenWidth - 32}
          height={220}
          chartConfig={chartConfig}
          accessor="population"
          backgroundColor="transparent"
          paddingLeft="15"
          style={styles.chart}
        />
      </View>

      {/* Beta Table */}
      <View style={styles.tableSection}>
        <Text style={styles.chartTitle}>Asset Beta Coefficients</Text>
        {data.beta_table.map((row, index) => (
          <View key={index} style={styles.tableRow}>
            <Text style={styles.symbolText}>{row.symbol}</Text>
            <Text style={styles.betaText}>β: {row.beta.toFixed(2)}</Text>
            <Text style={[
              styles.changeText,
              { color: row.change_24h >= 0 ? '#10b981' : '#ef4444' }
            ]}>
              {row.change_24h >= 0 ? '+' : ''}{row.change_24h.toFixed(2)}%
            </Text>
            <Text style={[
              styles.riskText,
              { color: row.risk_color === 'red' ? '#ef4444' : 
                       row.risk_color === 'yellow' ? '#f59e0b' : '#10b981' }
            ]}>
              {row.risk_category}
            </Text>
          </View>
        ))}
      </View>

      {/* Insights */}
      <View style={styles.insightsSection}>
        <Text style={styles.chartTitle}>Trading Insights</Text>
        
        {data.insights.high_risk_opportunities.length > 0 && (
          <View style={styles.insightCard}>
            <Text style={styles.insightTitle}>High Risk Opportunities</Text>
            <Text style={styles.insightText}>
              {data.insights.high_risk_opportunities.join(', ')}
            </Text>
          </View>
        )}
        
        {data.insights.safe_performers.length > 0 && (
          <View style={styles.insightCard}>
            <Text style={styles.insightTitle}>Safe Performers</Text>
            <Text style={styles.insightText}>
              {data.insights.safe_performers.join(', ')}
            </Text>
          </View>
        )}
        
        {data.insights.avoid_list.length > 0 && (
          <View style={styles.insightCard}>
            <Text style={styles.insightTitle}>Consider Avoiding</Text>
            <Text style={styles.insightText}>
              {data.insights.avoid_list.join(', ')}
            </Text>
          </View>
        )}
      </View>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0c1a2b',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#0c1a2b',
  },
  loadingText: {
    color: '#ffbf00',
    marginTop: 10,
    fontSize: 16,
  },
  errorContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#0c1a2b',
    padding: 20,
  },
  errorText: {
    color: '#ef4444',
    fontSize: 16,
    textAlign: 'center',
  },
  header: {
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255, 191, 0, 0.2)',
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#ffbf00',
  },
  subtitle: {
    fontSize: 14,
    color: '#b8860b',
    marginTop: 4,
  },
  metricsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    padding: 16,
    justifyContent: 'space-between',
  },
  metricCard: {
    width: '48%',
    backgroundColor: 'rgba(255, 191, 0, 0.1)',
    padding: 16,
    borderRadius: 8,
    marginBottom: 12,
    alignItems: 'center',
  },
  metricValue: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#ff9900',
  },
  metricLabel: {
    fontSize: 12,
    color: '#ffbf00',
    marginTop: 4,
  },
  chartSection: {
    padding: 16,
  },
  chartTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#ffbf00',
    marginBottom: 12,
  },
  chart: {
    borderRadius: 16,
  },
  tableSection: {
    padding: 16,
  },
  tableRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255, 191, 0, 0.2)',
  },
  symbolText: {
    color: '#ffbf00',
    fontSize: 16,
    fontWeight: '600',
    flex: 1,
  },
  betaText: {
    color: '#ff9900',
    fontSize: 14,
    flex: 1,
  },
  changeText: {
    fontSize: 14,
    fontWeight: '600',
    flex: 1,
    textAlign: 'right',
  },
  riskText: {
    fontSize: 12,
    flex: 1.5,
    textAlign: 'right',
  },
  insightsSection: {
    padding: 16,
    marginBottom: 32,
  },
  insightCard: {
    backgroundColor: 'rgba(255, 191, 0, 0.05)',
    padding: 16,
    borderRadius: 8,
    marginBottom: 12,
    borderLeftWidth: 3,
    borderLeftColor: '#ff9900',
  },
  insightTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#ff9900',
    marginBottom: 8,
  },
  insightText: {
    fontSize: 14,
    color: '#ffbf00',
    lineHeight: 20,
  },
});

export default BetaDashboard;