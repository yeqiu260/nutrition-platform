
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface AdminUser {
    id: string;
    username: string;
    role: string;
}

interface AdminState {
    adminUser: AdminUser | null;
    setAdminUser: (user: AdminUser | null) => void;
    isAuthenticated: boolean;
}

export const useAdminStore = create<AdminState>()(
    persist(
        (set) => ({
            adminUser: null,
            isAuthenticated: false,
            setAdminUser: (user) => set({ adminUser: user, isAuthenticated: !!user }),
        }),
        {
            name: 'admin-storage',
        }
    )
);
