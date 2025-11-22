import { useState, useEffect } from 'react'
import { marketApi } from '../services/api'
import './StockChart.css'

interface ChartData {
  date: string
  open: number
  high: number
  low: number
  close: number
  volume: number
  amount: number
}

interface ChartResponse {
  stock_code: string
  period: string
  start_date: string
  end_date: string
  current_price: number
  chart_data: ChartData[]
}

interface TrendData {
  date: string
  time: string
  price: number
  volume: number
}

interface TrendResponse {
  stock_code: string
  current_price: number
  change_price: number
  change_rate: number
  trend_data: TrendData[]
}

function StockChart() {
  const [stockCode, setStockCode] = useState('005930')
  const [period, setPeriod] = useState<'D' | 'W' | 'M' | 'Y'>('D')
  const [chartData, setChartData] = useState<ChartResponse | null>(null)
  const [trendData, setTrendData] = useState<TrendResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'chart' | 'trend'>('chart')

  // 날짜 계산 (기본값: 최근 30일)
  const getDefaultDates = () => {
    const end = new Date()
    const start = new Date()
    
    if (period === 'D') {
      start.setDate(start.getDate() - 30)
    } else if (period === 'W') {
      start.setDate(start.getDate() - 30 * 7)
    } else if (period === 'M') {
      start.setMonth(start.getMonth() - 12)
    } else {
      start.setFullYear(start.getFullYear() - 5)
    }
    
    return {
      start: start.toISOString().slice(0, 10).replace(/-/g, ''),
      end: end.toISOString().slice(0, 10).replace(/-/g, '')
    }
  }

  const fetchChartData = async () => {
    if (!stockCode.trim()) return

    setLoading(true)
    setError(null)
    try {
      const dates = getDefaultDates()
      const response = await marketApi.getChart(stockCode.trim(), dates.start, dates.end, period)
      setChartData(response.data)
    } catch (err: any) {
      setError(err.response?.data?.detail || '차트 데이터를 불러오는데 실패했습니다.')
      setChartData(null)
    } finally {
      setLoading(false)
    }
  }

  const fetchTrendData = async () => {
    if (!stockCode.trim()) return

    setLoading(true)
    setError(null)
    try {
      const response = await marketApi.getPriceTrend(stockCode.trim())
      setTrendData(response.data)
    } catch (err: any) {
      setError(err.response?.data?.detail || '추세 데이터를 불러오는데 실패했습니다.')
      setTrendData(null)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (activeTab === 'chart') {
      fetchChartData()
    } else {
      fetchTrendData()
    }
  }, [stockCode, period, activeTab])

  const formatDate = (dateStr: string) => {
    if (dateStr.length === 8) {
      return `${dateStr.slice(0, 4)}-${dateStr.slice(4, 6)}-${dateStr.slice(6, 8)}`
    }
    return dateStr
  }

  const formatNumber = (num: number) => {
    return new Intl.NumberFormat('ko-KR').format(num)
  }

  return (
    <div className="stock-chart">
      <div className="card">
        <div className="chart-header">
          <h2>차트 & 추세 분석</h2>
          <div className="chart-controls">
            <input
              type="text"
              className="input"
              placeholder="종목코드 (예: 005930)"
              value={stockCode}
              onChange={(e) => setStockCode(e.target.value)}
              style={{ width: '150px' }}
            />
            <select
              className="input"
              value={period}
              onChange={(e) => setPeriod(e.target.value as 'D' | 'W' | 'M' | 'Y')}
              style={{ width: '100px' }}
            >
              <option value="D">일봉</option>
              <option value="W">주봉</option>
              <option value="M">월봉</option>
              <option value="Y">년봉</option>
            </select>
            <button
              className="button button-primary"
              onClick={() => activeTab === 'chart' ? fetchChartData() : fetchTrendData()}
              disabled={loading}
            >
              {loading ? '로딩 중...' : '조회'}
            </button>
          </div>
        </div>

        <div className="chart-tabs">
          <button
            className={`tab-button ${activeTab === 'chart' ? 'active' : ''}`}
            onClick={() => setActiveTab('chart')}
          >
            차트
          </button>
          <button
            className={`tab-button ${activeTab === 'trend' ? 'active' : ''}`}
            onClick={() => setActiveTab('trend')}
          >
            추세
          </button>
        </div>

        {error && <div className="error">{error}</div>}

        {activeTab === 'chart' && chartData && (
          <div className="chart-content">
            <div className="chart-summary">
              <div className="summary-item">
                <span className="label">현재가</span>
                <span className="value">{formatNumber(chartData.current_price)}원</span>
              </div>
              <div className="summary-item">
                <span className="label">기간</span>
                <span className="value">
                  {formatDate(chartData.start_date)} ~ {formatDate(chartData.end_date)}
                </span>
              </div>
              <div className="summary-item">
                <span className="label">데이터 수</span>
                <span className="value">{chartData.chart_data.length}건</span>
              </div>
            </div>

            <div className="chart-table">
              <table>
                <thead>
                  <tr>
                    <th>날짜</th>
                    <th>시가</th>
                    <th>고가</th>
                    <th>저가</th>
                    <th>종가</th>
                    <th>거래량</th>
                    <th>거래대금</th>
                  </tr>
                </thead>
                <tbody>
                  {chartData.chart_data.slice(0, 20).map((item, index) => (
                    <tr key={index}>
                      <td>{formatDate(item.date)}</td>
                      <td>{formatNumber(item.open)}</td>
                      <td className={item.high >= item.open ? 'up' : 'down'}>
                        {formatNumber(item.high)}
                      </td>
                      <td className={item.low <= item.open ? 'down' : 'up'}>
                        {formatNumber(item.low)}
                      </td>
                      <td className={item.close >= item.open ? 'up' : 'down'}>
                        {formatNumber(item.close)}
                      </td>
                      <td>{formatNumber(item.volume)}</td>
                      <td>{formatNumber(item.amount)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {chartData.chart_data.length > 20 && (
                <p className="table-note">최근 20건만 표시됩니다. (전체 {chartData.chart_data.length}건)</p>
              )}
            </div>
          </div>
        )}

        {activeTab === 'trend' && trendData && (
          <div className="trend-content">
            <div className="trend-summary">
              <div className="summary-item">
                <span className="label">현재가</span>
                <span className="value">{formatNumber(trendData.current_price)}원</span>
              </div>
              <div className="summary-item">
                <span className="label">전일 대비</span>
                <span className={`value ${trendData.change_price >= 0 ? 'up' : 'down'}`}>
                  {trendData.change_price >= 0 ? '+' : ''}
                  {formatNumber(trendData.change_price)}원 ({trendData.change_rate >= 0 ? '+' : ''}
                  {trendData.change_rate}%)
                </span>
              </div>
              <div className="summary-item">
                <span className="label">추이 데이터</span>
                <span className="value">{trendData.trend_data.length}건</span>
              </div>
            </div>

            <div className="trend-table">
              <table>
                <thead>
                  <tr>
                    <th>날짜</th>
                    <th>시간</th>
                    <th>가격</th>
                    <th>거래량</th>
                  </tr>
                </thead>
                <tbody>
                  {trendData.trend_data.slice(0, 30).map((item, index) => (
                    <tr key={index}>
                      <td>{formatDate(item.date)}</td>
                      <td>
                        {item.time.slice(0, 2)}:{item.time.slice(2, 4)}:{item.time.slice(4, 6)}
                      </td>
                      <td>{formatNumber(item.price)}</td>
                      <td>{formatNumber(item.volume)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {trendData.trend_data.length > 30 && (
                <p className="table-note">최근 30건만 표시됩니다. (전체 {trendData.trend_data.length}건)</p>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default StockChart


