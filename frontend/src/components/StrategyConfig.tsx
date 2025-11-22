import { useState, useEffect } from 'react'
import { strategyApi, autoTradingApi } from '../services/api'
import './StrategyConfig.css'

interface Strategy {
  id: number
  name: string
  description: string | null
  strategy_type: string | null
  is_active: boolean
  config: any
  created_at: string
  updated_at: string
}

interface StrategyType {
  type: string
  name: string
  description: string
  best_for: string
  risk_level: string
  recommended: boolean
  performance_note: string
  default_config: any
}

function StrategyConfig() {
  const [strategies, setStrategies] = useState<Strategy[]>([])
  const [strategyTypes, setStrategyTypes] = useState<StrategyType[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [autoTradingStatus, setAutoTradingStatus] = useState<any>(null)
  const [executing, setExecuting] = useState(false)
  const [executeResult, setExecuteResult] = useState<any>(null)
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    strategy_type: '',
    config: {} as any,
    stock_selection_mode: 'watchlist' as 'watchlist' | 'auto' | 'ranking',
    auto_selection_config: {} as any,
  })

  const fetchStrategies = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await strategyApi.getStrategies()
      setStrategies(response.data)
    } catch (err: any) {
      setError(err.response?.data?.detail || '전략 목록을 불러오는데 실패했습니다.')
    } finally {
      setLoading(false)
    }
  }

  const fetchStrategyTypes = async () => {
    try {
      const response = await strategyApi.getStrategyTypes()
      setStrategyTypes(response.data.strategy_types || [])
    } catch (err: any) {
      console.error('전략 타입 목록 불러오기 실패:', err)
    }
  }

  useEffect(() => {
    fetchStrategies()
    fetchStrategyTypes()
    fetchAutoTradingStatus()
  }, [])

  const fetchAutoTradingStatus = async () => {
    try {
      const response = await autoTradingApi.getStatus()
      setAutoTradingStatus(response.data)
    } catch (err: any) {
      console.error('자동매매 상태 조회 실패:', err)
    }
  }

  const handleExecuteAutoTrading = async () => {
    if (!confirm('자동매매를 실행하시겠습니까? 활성화된 전략에 따라 실제 주문이 발생할 수 있습니다.')) {
      return
    }

    setExecuting(true)
    setExecuteResult(null)
    setError(null)

    try {
      const response = await autoTradingApi.execute()
      setExecuteResult(response.data)
      // 전략 목록 새로고침
      fetchStrategies()
      // 주문 내역도 새로고침될 수 있도록 (필요시)
    } catch (err: any) {
      setError(err.response?.data?.detail || '자동매매 실행에 실패했습니다.')
    } finally {
      setExecuting(false)
    }
  }

  const handleStrategyTypeChange = (type: string) => {
    const selectedType = strategyTypes.find(st => st.type === type)
    if (selectedType) {
      setFormData({
        name: selectedType.name,
        description: selectedType.description,
        strategy_type: type,
        config: selectedType.default_config,
      })
    } else {
      setFormData({
        ...formData,
        strategy_type: type,
      })
    }
  }

  const handleCreateStrategy = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await strategyApi.createStrategy({
        name: formData.name,
        description: formData.description,
        strategy_type: formData.strategy_type,
        config: formData.config,
        stock_selection_mode: formData.stock_selection_mode,
        auto_selection_config: formData.stock_selection_mode !== 'watchlist' ? formData.auto_selection_config : undefined,
      })
      setShowForm(false)
      setFormData({ 
        name: '', 
        description: '', 
        strategy_type: '', 
        config: {},
        stock_selection_mode: 'watchlist',
        auto_selection_config: {},
      })
      fetchStrategies()
    } catch (err: any) {
      setError(err.response?.data?.detail || '전략 생성에 실패했습니다.')
    }
  }

  const handleToggleActive = async (strategy: Strategy) => {
    try {
      if (strategy.is_active) {
        await strategyApi.deactivateStrategy(strategy.id)
      } else {
        await strategyApi.activateStrategy(strategy.id)
      }
      fetchStrategies()
      fetchAutoTradingStatus() // 상태도 새로고침
    } catch (err: any) {
      setError(err.response?.data?.detail || '전략 상태 변경에 실패했습니다.')
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('정말 삭제하시겠습니까?')) return
    try {
      await strategyApi.deleteStrategy(id)
      fetchStrategies()
    } catch (err: any) {
      setError(err.response?.data?.detail || '전략 삭제에 실패했습니다.')
    }
  }

  if (loading) {
    return <div className="loading">전략 목록을 불러오는 중...</div>
  }

  return (
    <div className="strategy-config">
      <div className="card">
        <div className="card-header">
          <h2>전략 관리</h2>
          <div className="header-actions">
            {autoTradingStatus && autoTradingStatus.active_strategies > 0 && (
              <button
                className="button button-success"
                onClick={handleExecuteAutoTrading}
                disabled={executing}
                title="활성화된 전략에 따라 관심종목 또는 자동 선택된 종목에 대해 자동매매를 실행합니다"
              >
                {executing ? '자동매매 실행 중...' : '자동매매 실행'}
              </button>
            )}
            <button
              className="button button-primary"
              onClick={() => setShowForm(!showForm)}
            >
              {showForm ? '취소' : '새 전략 추가'}
            </button>
          </div>
        </div>

        {autoTradingStatus && (
          <div className="status-control-grid">
            {/* 왼쪽: 통계 정보 */}
            <div className="status-section">
              <h3>현재 상태</h3>
              <div className="status-items">
                <div className="status-item">
                  <span className="label">활성 전략</span>
                  <span className="value">{autoTradingStatus.active_strategies}개</span>
                </div>
                <div className="status-item">
                  <span className="label">관심종목</span>
                  <span className="value">{autoTradingStatus.watchlist_count}개</span>
                </div>
                {autoTradingStatus.scheduler && (
                  <div className="status-item">
                    <span className="label">자동 실행</span>
                    <span className={`value ${autoTradingStatus.scheduler.is_running ? 'running' : 'stopped'}`}>
                      {autoTradingStatus.scheduler.is_running 
                        ? (autoTradingStatus.scheduler.schedule_type === 'daily' 
                            ? '실행 중 (매일 오전 9시 5분)'
                            : `실행 중 (${autoTradingStatus.scheduler.interval_seconds}초 간격)`)
                        : '중지됨'}
                    </span>
                  </div>
                )}
                {autoTradingStatus.market && (
                  <div className="status-item">
                    <span className="label">시장 상태</span>
                    <span className={`value ${autoTradingStatus.market.is_open ? 'open' : 'closed'}`}>
                      {autoTradingStatus.market.is_open ? '개장' : '폐장'}
                    </span>
                    {!autoTradingStatus.market.is_open && autoTradingStatus.market.next_open_time && (
                      <div className="market-hint">
                        다음 개장: {new Date(autoTradingStatus.market.next_open_time).toLocaleString('ko-KR', { 
                          month: 'short', 
                          day: 'numeric', 
                          hour: '2-digit', 
                          minute: '2-digit' 
                        })}
                      </div>
                    )}
                  </div>
                )}
              </div>
              {autoTradingStatus.active_strategies === 0 && (
                <p className="status-hint">
                  전략을 활성화하면 자동매매를 실행할 수 있습니다.
                </p>
              )}
              {autoTradingStatus.active_strategies > 0 && !autoTradingStatus.scheduler?.is_running && (
                <p className="status-hint">
                  자동 실행을 시작하면 설정한 주기에 따라 자동으로 매매를 체크하고 실행합니다.
                </p>
              )}
            </div>

            {/* 오른쪽: 자동 실행 설정 */}
            {autoTradingStatus.active_strategies > 0 && (
              <div className="control-section">
                <h3>자동 실행 설정</h3>
                {!autoTradingStatus.scheduler?.is_running ? (
                  <div className="scheduler-start">
                    <div className="schedule-options">
                      <label className="schedule-option">
                        <input
                          type="radio"
                          name="scheduleType"
                          value="interval"
                          defaultChecked
                        />
                        <span>1분마다 실행 (실시간 모니터링)</span>
                      </label>
                      <label className="schedule-option">
                        <input
                          type="radio"
                          name="scheduleType"
                          value="daily"
                        />
                        <span>하루 한번 실행 (매일 오전 9시 5분)</span>
                      </label>
                    </div>
                    <p className="schedule-hint">
                      시장이 열려있을 때만 거래가 실행됩니다. (09:00 ~ 15:30)
                    </p>
                    <button
                      className="button button-success button-full"
                      onClick={async () => {
                        try {
                          const scheduleType = (document.querySelector('input[name="scheduleType"]:checked') as HTMLInputElement)?.value as 'interval' | 'daily'
                          await autoTradingApi.startScheduler(60, scheduleType)
                          fetchAutoTradingStatus()
                        } catch (err: any) {
                          setError(err.response?.data?.detail || '자동 실행 시작에 실패했습니다.')
                        }
                      }}
                    >
                      자동 실행 시작
                    </button>
                  </div>
                ) : (
                  <div className="scheduler-stop">
                    <p>
                      자동 실행이 활성화되어 있습니다. 
                      {autoTradingStatus.scheduler.schedule_type === 'daily' 
                        ? ' (매일 오전 9시 5분 실행)'
                        : ` (${autoTradingStatus.scheduler.interval_seconds}초 간격)`}
                    </p>
                    <button
                      className="button button-danger button-full"
                      onClick={async () => {
                        if (!confirm('자동 실행을 중지하시겠습니까?')) return
                        try {
                          await autoTradingApi.stopScheduler()
                          fetchAutoTradingStatus()
                        } catch (err: any) {
                          setError(err.response?.data?.detail || '자동 실행 중지에 실패했습니다.')
                        }
                      }}
                    >
                      자동 실행 중지
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {executeResult && (
          <div className="execute-result">
            <h4>자동매매 실행 결과</h4>
            <p>{executeResult.message}</p>
            {executeResult.signals && executeResult.signals.length > 0 && (
              <div className="signals-list">
                <p><strong>처리된 신호: {executeResult.signals.length}개</strong></p>
                <ul>
                  {executeResult.signals.slice(0, 5).map((signal: any, index: number) => (
                    <li key={index}>
                      {signal.action} {signal.stock_code} {signal.quantity}주 @ {signal.price}원
                      {signal.status === 'executed' && ' [완료]'}
                      {signal.status === 'failed' && ` [실패: ${signal.error}]`}
                    </li>
                  ))}
                </ul>
                {executeResult.signals.length > 5 && (
                  <p className="more-signals">... 외 {executeResult.signals.length - 5}개</p>
                )}
              </div>
            )}
          </div>
        )}

        {error && <div className="error">{error}</div>}

        {showForm && (
          <form onSubmit={handleCreateStrategy} className="strategy-form">
            <div className="form-group">
              <label className="label">전략 타입 선택 *</label>
              <select
                className="input"
                value={formData.strategy_type}
                onChange={(e) => handleStrategyTypeChange(e.target.value)}
                required
              >
                <option value="">전략 타입을 선택하세요</option>
                {strategyTypes.map((type) => (
                  <option key={type.type} value={type.type}>
                    {type.name} {type.recommended ? '⭐ 추천' : ''}
                  </option>
                ))}
              </select>
              {formData.strategy_type && (
                <div className="strategy-type-info">
                  {(() => {
                    const selected = strategyTypes.find(st => st.type === formData.strategy_type)
                    if (!selected) return null
                    return (
                      <div>
                        <p><strong>설명:</strong> {selected.description}</p>
                        <p><strong>적합한 시장:</strong> {selected.best_for}</p>
                        <p><strong>리스크:</strong> {selected.risk_level}</p>
                        <p><strong>성능:</strong> {selected.performance_note}</p>
                      </div>
                    )
                  })()}
                </div>
              )}
            </div>
            <div className="form-group">
              <label className="label">전략명 *</label>
              <input
                type="text"
                className="input"
                value={formData.name}
                onChange={(e) =>
                  setFormData({ ...formData, name: e.target.value })
                }
                required
              />
            </div>
            <div className="form-group">
              <label className="label">설명</label>
              <textarea
                className="input"
                rows={3}
                value={formData.description}
                onChange={(e) =>
                  setFormData({ ...formData, description: e.target.value })
                }
              />
            </div>
            
            <div className="form-group">
              <label className="label">종목 선택 모드</label>
              <select
                className="input"
                value={formData.stock_selection_mode}
                onChange={(e) =>
                  setFormData({ 
                    ...formData, 
                    stock_selection_mode: e.target.value as 'watchlist' | 'auto' | 'ranking' 
                  })
                }
              >
                <option value="watchlist">관심종목 (사용자가 지정한 종목만) ⭐ 추천</option>
                <option value="auto">자동 선택 (등락률/거래량 기반)</option>
                <option value="ranking">랭킹 기반 (상위 종목 자동 선택)</option>
              </select>
              <p className="form-hint">
                {formData.stock_selection_mode === 'watchlist' && (
                  <>초보자에게 안전한 방식입니다. 관심종목에 추가한 종목들에 대해서만 전략이 실행됩니다.</>
                )}
                 {formData.stock_selection_mode === 'auto' && (
                   <>시스템이 자동으로 종목을 선택합니다. 예상치 못한 종목에 투자될 수 있으니 주의하세요.</>
                 )}
                 {formData.stock_selection_mode === 'ranking' && (
                   <>등락률순위나 거래량순위 상위 종목을 자동으로 선택합니다.</>
                 )}
              </p>
            </div>

            {formData.stock_selection_mode !== 'watchlist' && (
              <div className="form-group">
                <label className="label">자동 선택 설정</label>
                <div className="auto-selection-config">
                  <div className="config-item">
                    <label>최대 선택 종목 수</label>
                    <input
                      type="number"
                      className="input"
                      min="1"
                      max="50"
                      value={formData.auto_selection_config?.max_stocks || 10}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          auto_selection_config: {
                            ...formData.auto_selection_config,
                            max_stocks: parseInt(e.target.value) || 10,
                          },
                        })
                      }
                    />
                  </div>
                  <div className="config-item">
                    <label>최소 등락률 (%)</label>
                    <input
                      type="number"
                      className="input"
                      min="0"
                      step="0.1"
                      value={formData.auto_selection_config?.criteria?.min_change_rate || 3.0}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          auto_selection_config: {
                            ...formData.auto_selection_config,
                            criteria: {
                              ...formData.auto_selection_config?.criteria,
                              min_change_rate: parseFloat(e.target.value) || 3.0,
                            },
                          },
                        })
                      }
                    />
                  </div>
                  <div className="config-item">
                    <label>최소 거래량</label>
                    <input
                      type="number"
                      className="input"
                      min="0"
                      value={formData.auto_selection_config?.criteria?.min_volume || 1000000}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          auto_selection_config: {
                            ...formData.auto_selection_config,
                            criteria: {
                              ...formData.auto_selection_config?.criteria,
                              min_volume: parseInt(e.target.value) || 1000000,
                            },
                          },
                        })
                      }
                    />
                  </div>
                </div>
              </div>
            )}
            
            <button type="submit" className="button button-primary">
              전략 생성
            </button>
          </form>
        )}

        {strategies.length === 0 ? (
          <div className="empty-state">
            <p>등록된 전략이 없습니다.</p>
            <p className="empty-state-hint">위의 "새 전략 추가" 버튼을 클릭하여 전략을 생성하세요.</p>
          </div>
        ) : (
          <div className="strategy-list">
            {strategies.map((strategy) => (
              <div key={strategy.id} className="strategy-item">
                <div className="strategy-header">
                  <h3>{strategy.name}</h3>
                  <div className="strategy-actions">
                    <button
                      className={`button ${
                        strategy.is_active ? 'button-danger' : 'button-primary'
                      }`}
                      onClick={() => handleToggleActive(strategy)}
                    >
                      {strategy.is_active ? '비활성화' : '활성화'}
                    </button>
                    <button
                      className="button button-danger"
                      onClick={() => handleDelete(strategy.id)}
                    >
                      삭제
                    </button>
                  </div>
                </div>
                {strategy.description && (
                  <p className="strategy-description">{strategy.description}</p>
                )}
                <div className="strategy-meta">
                  <span className="strategy-type">
                    유형: {strategy.strategy_type || '미지정'}
                  </span>
                  <span
                    className={`strategy-status ${
                      strategy.is_active ? 'active' : 'inactive'
                    }`}
                  >
                    {strategy.is_active ? '활성' : '비활성'}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default StrategyConfig


