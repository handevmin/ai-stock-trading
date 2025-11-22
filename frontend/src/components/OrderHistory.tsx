import { useState, useEffect } from 'react'
import { orderApi } from '../services/api'
import './OrderHistory.css'

interface Order {
  order_no: string
  stock_code: string
  stock_name: string
  side: string
  order_type: string
  quantity: number
  price: number
  executed_quantity: number
  executed_price: number
  status: string
  order_time: string
}

function OrderHistory() {
  const [orders, setOrders] = useState<Order[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchOrders = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await orderApi.getHistory()
      setOrders(response.data.orders || [])
    } catch (err: any) {
      setError(err.response?.data?.detail || '주문 내역을 불러오는데 실패했습니다.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchOrders()
    const interval = setInterval(fetchOrders, 10000) // 10초마다 갱신
    return () => clearInterval(interval)
  }, [])

  if (loading) {
    return <div className="loading">주문 내역을 불러오는 중...</div>
  }

  if (error) {
    return <div className="error">{error}</div>
  }

  return (
    <div className="order-history">
      <div className="card">
        <div className="card-header">
          <h2>주문 내역</h2>
          <button className="button button-primary" onClick={fetchOrders}>
            새로고침
          </button>
        </div>
        {orders.length === 0 ? (
          <div className="empty-state">주문 내역이 없습니다.</div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>주문번호</th>
                <th>종목명</th>
                <th>종목코드</th>
                <th>구분</th>
                <th>주문유형</th>
                <th>주문수량</th>
                <th>주문가격</th>
                <th>체결수량</th>
                <th>체결가격</th>
                <th>상태</th>
                <th>주문시간</th>
              </tr>
            </thead>
            <tbody>
              {orders.map((order) => (
                <tr key={order.order_no}>
                  <td>{order.order_no}</td>
                  <td>{order.stock_name}</td>
                  <td>{order.stock_code}</td>
                  <td
                    className={
                      order.side === '매수' || order.side === 'BUY'
                        ? 'buy'
                        : 'sell'
                    }
                  >
                    {order.side}
                  </td>
                  <td>{order.order_type}</td>
                  <td>{order.quantity.toLocaleString()}주</td>
                  <td>{order.price.toLocaleString()}원</td>
                  <td>{order.executed_quantity.toLocaleString()}주</td>
                  <td>
                    {order.executed_price
                      ? `${order.executed_price.toLocaleString()}원`
                      : '-'}
                  </td>
                  <td>{order.status}</td>
                  <td>{order.order_time}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

export default OrderHistory



