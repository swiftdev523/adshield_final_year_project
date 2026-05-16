# AdShield

**AI-Powered Mobile Security & Privacy Protection**

AdShield is a React Native mobile application built with Expo that helps users protect their Android devices from adware, spam notifications, and potentially dangerous applications. The app provides comprehensive APK scanning, real-time notification monitoring, and intelligent risk assessment powered by AI.

---

## 🎯 Overview

AdShield empowers users to make informed decisions about the apps they install and use on their devices. By analyzing APK files and monitoring notification patterns, AdShield identifies potential security threats, privacy risks, and spam behavior before they can harm your device or compromise your data.

---

## ✨ Features

### 🏠 **Home Dashboard**
- **Protection Status Overview**: Real-time display of device security status
- **Quick Stats**: View total apps scanned, threats detected, and overall security score
- **Recent Scans**: Quick access to recently analyzed APK files with risk indicators
- **Activity Feed**: Chronological timeline of security events and detected threats
- **Quick Scan Access**: One-tap navigation to APK scanner

### 🔍 **APK Scanner**
- **File Upload & Analysis**: Select and scan APK files from device storage
- **AI-Powered Risk Assessment**: Intelligent scoring system (0-100) to evaluate app safety
- **Risk Score Visualization**: Interactive circular meter displaying risk levels
  - **Safe** (0-40): Green indicator
  - **Caution** (41-70): Yellow/orange indicator  
  - **Dangerous** (71-100): Red indicator
- **Permission Analysis**: Detailed breakdown of app permissions with risk categorization
  - Internet Access
  - Contact Access
  - Location Services
  - Notification Permissions
- **Quick Scan Examples**: Pre-configured sample APKs for testing and demonstration
- **Detailed Results**: Comprehensive scan reports with actionable recommendations

### 🔔 **Notification Monitor**
- **Real-Time Monitoring**: Track notification patterns across installed apps (last 24 hours)
- **Spam Detection**: AI-powered identification of spam notification sources
- **App Ranking System**: Apps ranked by spam score and notification frequency
- **Statistical Overview**:
  - Total notifications received
  - Number of spam apps detected
  - Suspicious app count
- **Categorization Tags**:
  - **Spam**: High-frequency, low-value notifications
  - **Suspicious**: Potentially unwanted notification patterns
  - **Normal**: Standard notification behavior
- **Spam Alert Banner**: Dismissible warning when spam apps are detected
- **Filtering Options**: View apps by category (All, Spam, Suspicious, Normal)
- **Sorting Options**: Sort by frequency or spam score

### ⚙️ **Settings & Configuration**
- **Auto-Scan Downloads**: Automatically scan new APK files after download
- **Real-Time Protection**: Enable continuous notification monitoring for spam detection
- **Privacy Mode**: Hide sensitive app names in reports and activity logs

---

## 🏗️ Technical Architecture

### **Tech Stack**
- **Framework**: React Native 0.81.5
- **Platform**: Expo SDK 54
- **Navigation**: Expo Router 6 (file-based routing)
- **State Management**: Zustand 5
- **Styling**: NativeWind 4 (Tailwind CSS for React Native)
- **UI Components**: Custom component library with Lucide React Native icons
- **Typography**: Space Grotesk font family
- **Language**: TypeScript 5.9

### **Project Structure**
```
adshield/
├── app/                          # Expo Router pages
│   ├── (tabs)/                   # Tab-based navigation
│   │   ├── index.tsx            # Home screen
│   │   ├── scan.tsx             # APK scanner
│   │   ├── alerts.tsx           # Notification monitor
│   │   ├── settings.tsx         # Settings screen
│   │   └── _layout.tsx          # Tab navigation layout
│   ├── scan-result.tsx          # Scan results detail screen
│   └── _layout.tsx              # Root layout
├── components/                   # Reusable UI components
│   ├── alerts/                  # Alert-specific components
│   │   ├── NotificationListItem.tsx
│   │   ├── SpamBanner.tsx
│   │   └── StatBar.tsx
│   ├── home/                    # Home screen components
│   │   ├── ActivityFeed.tsx
│   │   ├── HomeStats.tsx
│   │   └── RecentScans.tsx
│   ├── scan/                    # Scanner components
│   │   ├── FilePicker.tsx
│   │   ├── PermissionItem.tsx
│   │   └── ScanExampleList.tsx
│   └── ui/                      # Base UI components
│       ├── Badge.tsx
│       ├── Card.tsx
│       ├── ProgressRing.tsx
│       └── RiskMeter.tsx
├── store/                       # Zustand state stores
│   ├── useScanStore.ts         # Scan state management
│   └── useAlertStore.ts        # Alert state management
├── lib/                         # Utilities and data
│   └── mockData.ts             # Mock data for development
└── assets/                      # Images and static files
```

### **Design System**

**Color Palette** (Dark Theme):
- **Background**: `#0B1020` (Deep navy)
- **Surface**: `#0D1426` (Elevated surfaces)
- **Surface High**: `#1A2642` (Highest elevation)
- **Accent**: `#58D6FF` (Cyan blue)
- **Safe**: `#22C55E` (Green)
- **Caution**: `#F59E0B` (Amber)
- **Danger**: `#EF4444` (Red)
- **Border**: `#22304A` (Subtle borders)
- **Text Primary**: `#F8FAFC` (White)
- **Text Muted**: `#8EA0C6` (Gray-blue)
- **Text Dim**: `#64748B` (Dimmed text)

**Typography**:
- **Headings**: Space Grotesk Bold (700)
- **Body**: Space Grotesk Regular (400)
- **Emphasis**: Space Grotesk Medium (500)

---

## 🚀 Getting Started

### **Prerequisites**
- Node.js 18+ and npm
- Expo CLI
- iOS Simulator (macOS) or Android Emulator

### **Installation**

1. Clone the repository:
```bash
git clone <repository-url>
cd adshield
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm start
```

4. Run on your preferred platform:
```bash
npm run ios      # iOS Simulator
npm run android  # Android Emulator
npm run web      # Web browser
```

---

## 📱 Current Implementation Status

### **Completed Features**
✅ Home dashboard with protection status  
✅ APK scanner interface with file picker  
✅ Risk score visualization and meter  
✅ Permission analysis display  
✅ Notification monitoring interface  
✅ Spam detection UI and ranking system  
✅ Settings screen with toggles  
✅ Tab-based navigation  
✅ Dark theme design system  
✅ State management with Zustand  
✅ Mock data for development and testing  

### **Using Mock Data**
Currently, the app uses mock data for demonstration purposes:
- Sample APK scan results
- Simulated notification patterns
- Pre-configured app rankings
- Example activity feed items

### **Future Enhancements**
🔄 Real APK file analysis integration  
🔄 Actual notification monitoring implementation  
🔄 Backend API integration for AI-powered analysis  
🔄 User authentication and cloud sync  
🔄 Historical data and trend analysis  
🔄 Export scan reports  
🔄 Scheduled automatic scans  
🔄 Whitelist/blacklist management  

---

## 🎨 UI/UX Highlights

- **Dark Mode First**: Optimized for low-light usage with a sophisticated dark theme
- **Glassmorphism Effects**: Subtle card glows and transparency for modern aesthetics
- **Smooth Animations**: React Native Reanimated for fluid transitions
- **Intuitive Navigation**: Bottom tab bar with clear iconography
- **Visual Feedback**: Color-coded risk indicators (green/yellow/red)
- **Accessibility**: High contrast ratios and readable typography
- **Responsive Layout**: Adapts to different screen sizes

---

## 📄 License

This project is private and proprietary.

---

## 🤝 Contributing

This is a private project. For questions or contributions, please contact the project maintainers.

---

**Built with ❤️ using React Native and Expo**
