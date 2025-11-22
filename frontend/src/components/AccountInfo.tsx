import { useState, useEffect } from 'react'
import { accountApi } from '../services/api'
import './AccountInfo.css'

interface AccountBalance {
  account_no: string
  total_balance: number
  available_balance: number
  invested_amount: number
  profit_loss: number
  profit_loss_rate: number
}

interface Holding {
  stock_code: string
  stock_name: string
  quantity: number
  average_price: number
  current_price: number
  profit_loss: number
  profit_loss_rate: number
}

function AccountInfo() {
  const [balance, setBalance] = useState<AccountBalance | null>(null)
  const [holdings, setHoldings] = useState<Holding[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchAccountInfo = async () => {
    try {
      setLoading(true)
      setError(null)

      const [balanceRes, holdingsRes] = await Promise.all([
        accountApi.getBalance(),
        accountApi.getHoldings(),
      ])

      setBalance(balanceRes.data)
      setHoldings(holdingsRes.data.holdings || [])
    } catch (err: any) {
      setError(err.response?.data?.detail || '계좌 정보를 불러오는데 실패했습니다.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchAccountInfo()
    const interval = setInterval(fetchAccountInfo, 30000) // 30초마다 갱신
    return () => clearInterval(interval)
  }, [])

  if (loading) {
    return <div className="loading">계좌 정보를 불러오는 중...</div>
  }

  if (error) {
    return <div className="error">{error}</div>
  }

  return (
    <div className="account-info">
      <div className="card">
        <div className="card-header">
          <h2>계좌 잔고</h2>
          <button className="button button-primary" onClick={fetchAccountInfo}>
            새로고침
          </button>
        </div>
        {balance && (
          <div className="balance-grid">
            <div className="balance-item">
              <div className="balance-label">총 자산</div>
              <div className="balance-value">
                {balance.total_balance.toLocaleString()}원
              </div>
            </div>
            <div className="balance-item">
              <div className="balance-label">가용 자산</div>
              <div className="balance-value">
                {balance.available_balance.toLocaleString()}원
              </div>
            </div>
            <div className="balance-item">
              <div className="balance-label">투자 원금</div>
              <div className="balance-value">
                {balance.invested_amount.toLocaleString()}원
              </div>
            </div>
            <div className="balance-item">
              <div className="balance-label">손익</div>
              <div
                className={`balance-value ${
                  balance.profit_loss >= 0 ? 'positive' : 'negative'
                }`}
              >
                {balance.profit_loss >= 0 ? '+' : ''}
                {balance.profit_loss.toLocaleString()}원 (
                {balance.profit_loss_rate.toFixed(2)}%)
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="card">
        <h2>보유 종목</h2>
        {holdings.length === 0 ? (
          <div className="empty-state">보유 종목이 없습니다.</div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>종목명</th>
                <th>종목코드</th>
                <th>보유수량</th>
                <th>평균단가</th>
                <th>현재가</th>
                <th>손익</th>
                <th>손익률</th>
              </tr>
            </thead>
            <tbody>
              {holdings.map((holding) => (
                <tr key={holding.stock_code}>
                  <td>{holding.stock_name}</td>
                  <td>{holding.stock_code}</td>
                  <td>{holding.quantity.toLocaleString()}주</td>
                  <td>{holding.average_price.toLocaleString()}원</td>
                  <td>{holding.current_price.toLocaleString()}원</td>
                  <td
                    className={
                      holding.profit_loss >= 0 ? 'positive' : 'negative'
                    }
                  >
                    {holding.profit_loss >= 0 ? '+' : ''}
                    {holding.profit_loss.toLocaleString()}원
                  </td>
                  <td
                    className={
                      holding.profit_loss_rate >= 0 ? 'positive' : 'negative'
                    }
                  >
                    {holding.profit_loss_rate >= 0 ? '+' : ''}
                    {holding.profit_loss_rate.toFixed(2)}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

export default AccountInfo



