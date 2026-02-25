'use client';

import { useEffect, useState } from 'react';
import { reviewApi, ReviewQueueItem, ReviewStatus, RiskLevel, ReviewStats } from '@/lib/api/admin';
import { useAdminStore } from '@/lib/store/admin';

const STATUS_OPTIONS: { value: ReviewStatus | ''; label: string }[] = [
  { value: '', label: '全部状态' },
  { value: 'PENDING', label: '待审核' },
  { value: 'IN_REVIEW', label: '审核中' },
  { value: 'APPROVED', label: '已批准' },
  { value: 'REJECTED', label: '已拒绝' },
];

const RISK_OPTIONS: { value: RiskLevel | ''; label: string }[] = [
  { value: '', label: '全部风险' },
  { value: 'CRITICAL', label: '严重' },
  { value: 'HIGH', label: '高' },
  { value: 'MEDIUM', label: '中' },
  { value: 'LOW', label: '低' },
];

const STATUS_LABELS: Record<ReviewStatus, { label: string; color: string }> = {
  PENDING: { label: '待审核', color: 'bg-yellow-100 text-yellow-700' },
  IN_REVIEW: { label: '审核中', color: 'bg-blue-100 text-blue-700' },
  APPROVED: { label: '已批准', color: 'bg-green-100 text-green-700' },
  REJECTED: { label: '已拒绝', color: 'bg-red-100 text-red-700' },
};

const RISK_LABELS: Record<RiskLevel, { label: string; color: string }> = {
  CRITICAL: { label: '严重', color: 'bg-red-500 text-white' },
  HIGH: { label: '高', color: 'bg-orange-500 text-white' },
  MEDIUM: { label: '中', color: 'bg-yellow-500 text-white' },
  LOW: { label: '低', color: 'bg-green-500 text-white' },
};

/**
 * 审核队列页面
 * 
 * 实现需求：
 * - 8.2: 案例列表
 * - 8.3, 8.4: 审核操作
 * - 8.5: 筛选
 */
export default function ReviewPage() {
  const { adminUser } = useAdminStore();
  const [items, setItems] = useState<ReviewQueueItem[]>([]);
  const [stats, setStats] = useState<ReviewStats | null>(null);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [selectedItem, setSelectedItem] = useState<ReviewQueueItem | null>(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [resolutionNote, setResolutionNote] = useState('');
  const [error, setError] = useState('');

  // 筛选条件
  const [statusFilter, setStatusFilter] = useState<ReviewStatus | ''>('');
  const [riskFilter, setRiskFilter] = useState<RiskLevel | ''>('');

  useEffect(() => {
    loadReviews();
    loadStats();
  }, [page, statusFilter, riskFilter]);

  const loadReviews = async () => {
    setLoading(true);
    setError('');
    try {
      const response = await reviewApi.getReviewList({
        status: statusFilter || undefined,
        risk_level: riskFilter || undefined,
        page,
        page_size: 20,
        include_detail: false,
      });
      setItems(response.items);
      setTotal(response.total);
    } catch (err) {
      console.error('Failed to load reviews:', err);
      setError('加载审核列表失败');
    } finally {
      setLoading(false);
    }
  };

  const loadStats = async () => {
    try {
      const data = await reviewApi.getStats();
      setStats(data);
    } catch (err) {
      console.error('Failed to load stats:', err);
    }
  };

  const loadDetail = async (reviewId: string) => {
    try {
      const detail = await reviewApi.getReviewDetail(reviewId);
      setSelectedItem(detail);
    } catch (err) {
      console.error('Failed to load detail:', err);
      setError('加载详情失败');
    }
  };

  const handleApprove = async () => {
    if (!selectedItem || !adminUser) return;
    setActionLoading(true);
    try {
      await reviewApi.approveReview(selectedItem.id, adminUser.id, resolutionNote || undefined);
      setSelectedItem(null);
      setResolutionNote('');
      await loadReviews();
      await loadStats();
    } catch (err) {
      setError('批准失败');
    } finally {
      setActionLoading(false);
    }
  };

  const handleReject = async () => {
    if (!selectedItem || !adminUser || !resolutionNote.trim()) {
      setError('请填写拒绝原因');
      return;
    }
    setActionLoading(true);
    try {
      await reviewApi.rejectReview(selectedItem.id, adminUser.id, resolutionNote);
      setSelectedItem(null);
      setResolutionNote('');
      await loadReviews();
      await loadStats();
    } catch (err) {
      setError('拒绝失败');
    } finally {
      setActionLoading(false);
    }
  };

  const totalPages = Math.ceil(total / 20);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">审核队列</h1>
        {stats && (
          <div className="flex items-center gap-4 text-sm">
            <span className="text-gray-500">
              待审核: <span className="font-medium text-gray-900">{stats.total_pending}</span>
            </span>
            {stats.pending_by_risk?.CRITICAL > 0 && (
              <span className="text-red-600">
                严重: <span className="font-medium">{stats.pending_by_risk.CRITICAL}</span>
              </span>
            )}
            {stats.pending_by_risk?.HIGH > 0 && (
              <span className="text-orange-600">
                高风险: <span className="font-medium">{stats.pending_by_risk.HIGH}</span>
              </span>
            )}
          </div>
        )}
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
          {error}
        </div>
      )}

      {/* 筛选器 */}
      <div className="bg-white rounded-xl shadow p-4">
        <div className="flex flex-wrap gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">状态</label>
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value as ReviewStatus | '');
                setPage(1);
              }}
              className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            >
              {STATUS_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">风险等级</label>
            <select
              value={riskFilter}
              onChange={(e) => {
                setRiskFilter(e.target.value as RiskLevel | '');
                setPage(1);
              }}
              className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            >
              {RISK_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* 列表 */}
      <div className="bg-white rounded-xl shadow overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="text-gray-500">加载中...</div>
          </div>
        ) : items.length === 0 ? (
          <div className="flex items-center justify-center h-64">
            <div className="text-gray-500">暂无审核案例</div>
          </div>
        ) : (
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  会话 ID
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  风险等级
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  状态
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  创建时间
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  操作
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {items.map((item) => (
                <tr key={item.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="text-sm font-mono text-gray-900">
                      {item.session_id.slice(0, 8)}...
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${RISK_LABELS[item.risk_level].color}`}>
                      {RISK_LABELS[item.risk_level].label}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${STATUS_LABELS[item.status].color}`}>
                      {STATUS_LABELS[item.status].label}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {new Date(item.created_at).toLocaleString()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <button
                      onClick={() => loadDetail(item.id)}
                      className="text-primary-600 hover:text-primary-700 text-sm font-medium"
                    >
                      查看详情
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {/* 分页 */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-6 py-4 border-t">
            <span className="text-sm text-gray-500">
              共 {total} 条，第 {page} / {totalPages} 页
            </span>
            <div className="flex gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-3 py-1 bg-gray-100 text-gray-700 rounded hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                上一页
              </button>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="px-3 py-1 bg-gray-100 text-gray-700 rounded hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                下一页
              </button>
            </div>
          </div>
        )}
      </div>

      {/* 详情弹窗 */}
      {selectedItem && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-4xl max-h-[90vh] overflow-hidden">
            <div className="flex items-center justify-between p-4 border-b">
              <div className="flex items-center gap-4">
                <h2 className="text-lg font-semibold">审核详情</h2>
                <span className={`px-2 py-1 rounded text-xs font-medium ${RISK_LABELS[selectedItem.risk_level].color}`}>
                  {RISK_LABELS[selectedItem.risk_level].label}
                </span>
                <span className={`px-2 py-1 rounded text-xs font-medium ${STATUS_LABELS[selectedItem.status].color}`}>
                  {STATUS_LABELS[selectedItem.status].label}
                </span>
              </div>
              <button
                onClick={() => {
                  setSelectedItem(null);
                  setResolutionNote('');
                }}
                className="text-gray-500 hover:text-gray-700"
              >
                ✕
              </button>
            </div>

            <div className="p-4 space-y-4 overflow-auto max-h-[calc(90vh-200px)]">
              {/* 问卷答案 */}
              {selectedItem.questionnaire_answers && (
                <div>
                  <h3 className="font-medium text-gray-900 mb-2">问卷答案</h3>
                  <div className="bg-gray-50 rounded-lg p-4 overflow-auto max-h-48">
                    <pre className="text-sm text-gray-700">
                      {JSON.stringify(selectedItem.questionnaire_answers, null, 2)}
                    </pre>
                  </div>
                </div>
              )}

              {/* 化验指标 */}
              {selectedItem.lab_metrics && (
                <div>
                  <h3 className="font-medium text-gray-900 mb-2">化验指标</h3>
                  <div className="bg-gray-50 rounded-lg p-4 overflow-auto max-h-48">
                    <pre className="text-sm text-gray-700">
                      {JSON.stringify(selectedItem.lab_metrics, null, 2)}
                    </pre>
                  </div>
                </div>
              )}

              {/* 推荐结果 */}
              {selectedItem.recommendations && (
                <div>
                  <h3 className="font-medium text-gray-900 mb-2">生成的推荐</h3>
                  <div className="bg-gray-50 rounded-lg p-4 overflow-auto max-h-48">
                    <pre className="text-sm text-gray-700">
                      {JSON.stringify(selectedItem.recommendations, null, 2)}
                    </pre>
                  </div>
                </div>
              )}

              {/* 审核备注 */}
              {(selectedItem.status === 'PENDING' || selectedItem.status === 'IN_REVIEW') && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    审核备注 {selectedItem.status === 'PENDING' ? '(拒绝时必填)' : ''}
                  </label>
                  <textarea
                    value={resolutionNote}
                    onChange={(e) => setResolutionNote(e.target.value)}
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    rows={3}
                    placeholder="请输入审核备注..."
                  />
                </div>
              )}

              {/* 已处理的备注 */}
              {selectedItem.resolution_note && (
                <div>
                  <h3 className="font-medium text-gray-900 mb-2">处理备注</h3>
                  <p className="text-gray-700 bg-gray-50 rounded-lg p-4">
                    {selectedItem.resolution_note}
                  </p>
                </div>
              )}
            </div>

            {/* 操作按钮 */}
            {(selectedItem.status === 'PENDING' || selectedItem.status === 'IN_REVIEW') && (
              <div className="flex justify-end gap-2 p-4 border-t">
                <button
                  onClick={() => {
                    setSelectedItem(null);
                    setResolutionNote('');
                  }}
                  className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
                >
                  取消
                </button>
                <button
                  onClick={handleReject}
                  disabled={actionLoading}
                  className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50"
                >
                  {actionLoading ? '处理中...' : '拒绝'}
                </button>
                <button
                  onClick={handleApprove}
                  disabled={actionLoading}
                  className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50"
                >
                  {actionLoading ? '处理中...' : '批准'}
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
