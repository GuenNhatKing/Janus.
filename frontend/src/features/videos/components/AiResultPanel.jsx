import Icon from '@/shared/components/Icon'
import { ErrorNote, Spinner } from '@/shared/components/Feedback'
import { useAiAnalysis } from '../hooks/useAiAnalysis'

const JOB_LABEL = {
  pending: 'Đang chờ xử lý',
  running: 'Đang phân tích',
  succeeded: 'Hoàn tất',
  failed: 'Thất bại',
}

/**
 * Hiển thị kết quả phân tích THẬT từ GET /v1/videos/{id}/ai.
 * Panel tự poll cho tới khi job kết thúc (backend chạy job nền).
 */
export default function AiResultPanel({ videoId }) {
  const { result, loading, error } = useAiAnalysis(videoId)

  if (!videoId) return null

  return (
    <section className="ai-panel" aria-live="polite">
      <header className="ai-head">
        <div>
          <span className="overline">KẾT QUẢ PHÂN TÍCH</span>
          <h2>Trạng thái AI</h2>
        </div>
        <span className={`ai-state ${result?.job_status === 'succeeded' ? 'ok' : ''}`}>
          {loading && <Spinner label="Đang chờ kết quả" />}
          {JOB_LABEL[result?.job_status] || 'Đang lấy trạng thái'}
        </span>
      </header>

      {error && <ErrorNote>{error}</ErrorNote>}

      {result && (
        <>
          <div className="ai-labels">
            {result.labels.length === 0 && <p className="ai-empty">Chưa có nhãn nào được gán cho video này.</p>}
            {result.labels.map((label) => (
              <div className="ai-label" key={label.name}>
                <div className="ai-label-top">
                  <strong>{label.name}</strong>
                  <span className={`level level-${label.level.toLowerCase()}`}>{label.level}</span>
                </div>
                <div className="ai-bar">
                  <i style={{ width: `${Math.round(label.confidence * 100)}%` }} />
                </div>
                <span className="ai-score">{Math.round(label.confidence * 100)}% độ tin cậy</span>
              </div>
            ))}
          </div>

          <div className="ai-transcript">
            <span className="ai-transcript-title">
              <Icon name="spark" size={13} /> BẢN CHÉP LỜI
            </span>
            <p>{result.transcript || 'Không có bản chép lời cho video này.'}</p>
          </div>
        </>
      )}
    </section>
  )
}
