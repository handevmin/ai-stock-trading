import { useState, useEffect } from 'react'
import AccountInfo from './AccountInfo'
import OrderHistory from './OrderHistory'
import StrategyConfig from './StrategyConfig'
import StockSearch from './StockSearch'
import StockChart from './StockChart'
import StockRanking from './StockRanking'
import Watchlist from './Watchlist'
import './Dashboard.css'

function Dashboard() {
  const [activeTab, setActiveTab] = useState<'account' | 'orders' | 'strategy' | 'search' | 'chart' | 'ranking' | 'watchlist'>('account')

  const menuItems = [
    { id: 'account', label: '계좌 정보', icon: 'account' },
    { id: 'orders', label: '주문 내역', icon: 'orders' },
    { id: 'strategy', label: '전략 설정', icon: 'strategy' },
    { id: 'search', label: '종목 검색', icon: 'search' },
    { id: 'chart', label: '차트 & 추세', icon: 'chart' },
    { id: 'ranking', label: '실시간 랭킹', icon: 'ranking' },
    { id: 'watchlist', label: '관심종목', icon: 'watchlist' },
  ]

  return (
    <div className="dashboard">
      <nav className="main-nav">
        <div className="nav-container">
          {menuItems.map((item) => (
            <button
              key={item.id}
              className={`nav-item ${activeTab === item.id ? 'active' : ''}`}
              onClick={() => setActiveTab(item.id as any)}
            >
              <span className={`nav-icon icon-${item.icon}`}></span>
              <span className="nav-label">{item.label}</span>
            </button>
          ))}
        </div>
      </nav>

      <div className="tab-content">
        {activeTab === 'account' && <AccountInfo />}
        {activeTab === 'orders' && <OrderHistory />}
        {activeTab === 'strategy' && <StrategyConfig />}
        {activeTab === 'search' && <StockSearch />}
        {activeTab === 'chart' && <StockChart />}
        {activeTab === 'ranking' && <StockRanking />}
        {activeTab === 'watchlist' && <Watchlist />}
      </div>
    </div>
  )
}

export default Dashboard


