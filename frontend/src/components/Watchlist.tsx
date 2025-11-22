import { useState, useEffect } from 'react'
import { watchlistApi, marketApi } from '../services/api'
import './Watchlist.css'

interface WatchlistItem {
  id: number
  stock_code: string
  stock_name: string | null
  notes: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

function Watchlist() {
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showAddForm, setShowAddForm] = useState(false)
  const [stockCode, setStockCode] = useState('')
  const [notes, setNotes] = useState('')

  const fetchWatchlist = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await watchlistApi.getWatchlist()
      setWatchlist(response.data)
    } catch (err: any) {
      setError(err.response?.data?.detail || '관심종목 목록을 불러오는데 실패했습니다.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchWatchlist()
  }, [])

  const handleAddStock = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!stockCode.trim()) return

    try {
      // 종목 정보 조회
      let stockName = ''
      try {
        const stockInfo = await marketApi.getStockInfo(stockCode.trim())
        stockName = stockInfo.data.stock_name
      } catch {
        // 종목 정보 조회 실패해도 추가는 가능
      }

      await watchlistApi.addToWatchlist({
        stock_code: stockCode.trim(),
        stock_name: stockName,
        notes: notes.trim() || undefined,
      })

      setStockCode('')
      setNotes('')
      setShowAddForm(false)
      fetchWatchlist()
    } catch (err: any) {
      setError(err.response?.data?.detail || '관심종목 추가에 실패했습니다.')
    }
  }

  const handleRemoveStock = async (id: number) => {
    if (!confirm('정말 관심종목에서 제거하시겠습니까?')) return

    try {
      await watchlistApi.removeFromWatchlist(id)
      fetchWatchlist()
    } catch (err: any) {
      setError(err.response?.data?.detail || '관심종목 제거에 실패했습니다.')
    }
  }

  return (
    <div className="watchlist">
      <div className="card">
        <div className="card-header">
          <h2>관심종목 관리</h2>
          <button
            className="button button-primary"
            onClick={() => setShowAddForm(!showAddForm)}
          >
            {showAddForm ? '취소' : '종목 추가'}
          </button>
        </div>

        {error && <div className="error">{error}</div>}

        {showAddForm && (
          <form onSubmit={handleAddStock} className="add-form">
            <div className="form-group">
              <label className="label">종목코드</label>
              <input
                type="text"
                className="input"
                placeholder="종목코드 입력 (예: 005930)"
                value={stockCode}
                onChange={(e) => setStockCode(e.target.value)}
                required
              />
            </div>
            <div className="form-group">
              <label className="label">메모 (선택)</label>
              <textarea
                className="input"
                rows={2}
                placeholder="메모를 입력하세요"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
              />
            </div>
            <button type="submit" className="button button-primary">
              추가
            </button>
          </form>
        )}

        {loading ? (
          <div className="loading">로딩 중...</div>
        ) : watchlist.length === 0 ? (
          <div className="empty-state">
            <p>관심종목이 없습니다.</p>
            <p className="empty-state-hint">
              위의 "종목 추가" 버튼을 클릭하여 관심종목을 추가하세요.
            </p>
            <p className="info-text">
              💡 <strong>팁:</strong> 관심종목에 추가한 종목들에 대해서만 자동매매 전략이 실행됩니다.
            </p>
          </div>
        ) : (
          <div className="watchlist-table">
            <table>
              <thead>
                <tr>
                  <th>종목코드</th>
                  <th>종목명</th>
                  <th>메모</th>
                  <th>추가일</th>
                  <th>작업</th>
                </tr>
              </thead>
              <tbody>
                {watchlist.map((item) => (
                  <tr key={item.id}>
                    <td className="code-cell">{item.stock_code}</td>
                    <td className="name-cell">{item.stock_name || '-'}</td>
                    <td className="notes-cell">{item.notes || '-'}</td>
                    <td>{new Date(item.created_at).toLocaleDateString('ko-KR')}</td>
                    <td>
                      <button
                        className="button button-danger"
                        onClick={() => handleRemoveStock(item.id)}
                      >
                        제거
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="info-box">
              <p>
                <strong>총 {watchlist.length}개 종목</strong>
              </p>
              <p className="info-text">
                💡 <strong>중요:</strong> 관심종목을 추가하는 것만으로는 거래가 발생하지 않습니다.
                <br />
                거래를 하려면:
                <br />
                1. 전략 설정에서 전략을 생성하고 활성화하세요
                <br />
                2. 전략의 종목 선택 모드를 "관심종목"으로 설정하세요
                <br />
                3. 전략 설정 화면에서 "자동매매 실행" 버튼을 클릭하세요
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default Watchlist

