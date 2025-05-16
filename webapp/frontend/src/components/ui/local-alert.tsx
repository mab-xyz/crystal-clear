import React, { useState, useEffect, createContext, useContext } from 'react';

interface LocalAlertContextType {
    showLocalAlert: (message: string, duration?: number) => void;
    hideLocalAlert: () => void;
    localAlert: {
        visible: boolean;
        message: string;
    };
}

const LocalAlertContext = createContext<LocalAlertContextType | undefined>(undefined);

export const LocalAlertProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [localAlert, setLocalAlert] = useState({ visible: false, message: '' });
    const [timeoutId, setTimeoutId] = useState<NodeJS.Timeout | null>(null);

    const showLocalAlert = (message: string, duration = 3000) => {
        // Clear any existing timeout to prevent conflicts
        if (timeoutId) {
            clearTimeout(timeoutId);
        }

        setLocalAlert({ visible: true, message });

        // Set timeout to hide the alert after the specified duration
        const id = setTimeout(() => {
            setLocalAlert({ visible: false, message: '' });
        }, duration);

        setTimeoutId(id);
    };

    const hideLocalAlert = () => {
        setLocalAlert({ visible: false, message: '' });
        if (timeoutId) {
            clearTimeout(timeoutId);
            setTimeoutId(null);
        }
    };

    // Clean up timeout on unmount
    useEffect(() => {
        return () => {
            if (timeoutId) {
                clearTimeout(timeoutId);
            }
        };
    }, [timeoutId]);

    return (
        <LocalAlertContext.Provider value={{ showLocalAlert, hideLocalAlert, localAlert }}>
            {children}
            {localAlert.visible && <LocalAlert message={localAlert.message} />}
        </LocalAlertContext.Provider>
    );
};

export const useLocalAlert = (): LocalAlertContextType => {
    const context = useContext(LocalAlertContext);
    if (context === undefined) {
        throw new Error('useLocalAlert must be used within a LocalAlertProvider');
    }
    return context;
};

interface LocalAlertProps {
    message: string;
}

const LocalAlert: React.FC<LocalAlertProps> = ({ message }) => {
    return (
        <div
            style={{
                position: 'fixed',
                bottom: '20px',
                right: '20px',
                textAlign: 'left',
                backgroundColor: '#ffffff',
                border: '1px solid #f44336',
                color: '#2b2b2b',
                padding: '10px',
                borderRadius: '2px',
                zIndex: 9999,
                boxShadow: '0 4px 8px rgba(0, 0, 0, 0.2)',
                maxWidth: '400px',
                animation: '0.3s ease-out 0s 1 normal none running fadeIn',
                WebkitAnimation: '0.3s ease-out 0s 1 normal none running fadeIn',
                display: 'flex',
                alignItems: 'center'
            }}
        >
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style={{ marginRight: '0.5rem', flexShrink: 0 }}
            >
                <path fill-rule="evenodd" clip-rule="evenodd" d="M6 4H20V6H22V8V10V12H14V14H20V16H16V18H14V20H2V18V16V14V12V10V8H4V6H6V4ZM8 10H10V8H8V10Z" fill="#f44336" />
            </svg>

            {message}
            <style>
                {`
                @keyframes fadeIn {
                    from { opacity: 0; transform: translateY(10px); }
                    to { opacity: 1; transform: translateY(0); }
                }
                @-webkit-keyframes fadeIn {
                    from { opacity: 0; transform: translateY(10px); }
                    to { opacity: 1; transform: translateY(0); }
                }
                `}
            </style>
        </div>
    );
};

export default LocalAlert; 