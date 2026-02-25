
import { apiGet, apiPost } from '../api';

export type ReviewStatus = 'PENDING' | 'IN_REVIEW' | 'APPROVED' | 'REJECTED';
export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export interface ReviewQueueItem {
    id: string;
    session_id: string;
    user_id?: string;
    status: ReviewStatus;
    risk_level: RiskLevel;
    questionnaire_answers: any;
    lab_metrics?: any;
    recommendations: any; // RecommendationResult
    assigned_to?: string;
    resolution_note?: string;
    created_at: string;
    updated_at: string;
}

export interface ReviewStats {
    by_status: Record<ReviewStatus, number>;
    pending_by_risk: Record<RiskLevel, number>;
    total_pending: number;
}

export interface ReviewListResponse {
    items: ReviewQueueItem[];
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
}

export interface GetReviewListParams {
    status?: ReviewStatus;
    risk_level?: RiskLevel;
    assigned_to?: string;
    page?: number;
    page_size?: number;
    include_detail?: boolean;
}

export const reviewApi = {
    /**
     * Get review queue list
     */
    getReviewList: async (params: GetReviewListParams = {}) => {
        const query = new URLSearchParams();
        if (params.status) query.append('status', params.status);
        if (params.risk_level) query.append('risk_level', params.risk_level);
        if (params.assigned_to) query.append('assigned_to', params.assigned_to);
        if (params.page) query.append('page', params.page.toString());
        if (params.page_size) query.append('page_size', params.page_size.toString());
        if (params.include_detail) query.append('include_detail', 'true');

        return (await apiGet<ReviewListResponse>(`/api/review/list?${query.toString()}`)).data!;
    },

    /**
     * Get review stats
     */
    getStats: async () => {
        return (await apiGet<ReviewStats>('/api/review/stats')).data!;
    },

    /**
     * Get review detail
     */
    getReviewDetail: async (reviewId: string) => {
        return (await apiGet<ReviewQueueItem>(`/api/review/${reviewId}`)).data!;
    },

    /**
     * Approve review
     */
    approveReview: async (reviewId: string, reviewerId: string, resolutionNote?: string) => {
        return (await apiPost<ReviewQueueItem>(`/api/review/${reviewId}/approve?reviewer_id=${reviewerId}`, {
            resolution_note: resolutionNote
        })).data!;
    },

    /**
     * Reject review
     */
    rejectReview: async (reviewId: string, reviewerId: string, resolutionNote: string) => {
        return (await apiPost<ReviewQueueItem>(`/api/review/${reviewId}/reject?reviewer_id=${reviewerId}`, {
            resolution_note: resolutionNote
        })).data!;
    },

    /**
     * Assign reviewer
     */
    assignReviewer: async (reviewId: string, reviewerId: string) => {
        return (await apiPost<ReviewQueueItem>(`/api/review/${reviewId}/assign`, {
            reviewer_id: reviewerId
        })).data!;
    },
};
