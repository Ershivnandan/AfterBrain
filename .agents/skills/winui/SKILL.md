---
name: winui
description: WinUI 3 and Windows App SDK best practices covering modern desktop UI development, XAML controls, MVVM architecture, Mica/Acrylic backdrops, high-performance streaming chat interfaces, and Windows automation. Use when building or refactoring modern native Windows applications or desktop UI companions.
---

# WinUI 3 & Windows App SDK Development Guide

This skill provides best practices, patterns, and conventions for building modern native Windows desktop applications using WinUI 3 and the Windows App SDK.

## 1. Core Principles
- **Modern Windows Design**: Use Fluent Design principles (Mica backdrop, acrylic surfaces, standard corner radii, 60/120fps motion).
- **Correct Namespaces**: Always use `Microsoft.UI.Xaml.*` for WinUI 3, NEVER legacy UWP `Windows.UI.Xaml.*`.
- **Dispatcher Usage**: Use `Microsoft.UI.Dispatching.DispatcherQueue` instead of legacy `CoreDispatcher`.
- **Dialog Anchoring**: Always assign `dialog.XamlRoot = this.Content.XamlRoot;` before showing `ContentDialog` to avoid `InvalidOperationException`.
- **Window Management**: Use `AppWindow` and `Microsoft.UI.Windowing` for window positioning, styling, title bars, and always-on-top modes.

## 2. Project Structure & MVVM Architecture
```
MyApp/
├── App.xaml / App.xaml.cs          # Application lifecycle & theme bootstrapping
├── MainWindow.xaml / .cs           # Main window with Mica backdrop & NavigationView
├── Views/                          # XAML Pages & UserControls
│   ├── ChatView.xaml               # Real-time streaming AI chat interface
│   └── TimelineView.xaml           # Composition & asset inspector
├── ViewModels/                     # ObservableObject / CommunityToolkit.Mvvm
│   ├── ChatViewModel.cs
│   └── TimelineViewModel.cs
├── Models/                         # Data contracts (Asset, Layer, Keyframe)
└── Services/                       # IPC & Bridge to Adobe After Effects
    └── AfterEffectsBridgeService.cs
```

## 3. Streaming Chat UI Pattern in WinUI 3
In WinUI 3, use an `ItemsRepeater` or `ListView` with virtualized message templates:
- **User Message Bubble**: Right-aligned `Border` with `CornerRadius="16,16,4,16"` and subtle purple/blue gradient.
- **AI Response Bubble**: Left-aligned `Border` with `CornerRadius="16,16,16,4"` and dark obsidian acrylic background.
- **Token Streaming**: Update the observable message text via `DispatcherQueue.TryEnqueue(...)` so streaming tokens render without UI freezing.
- **Auto-Scroll**: Call `ScrollViewer.ChangeView(null, ScrollViewer.ScrollableHeight, null, false)` on every new token batch.

## 4. Bridge & Adobe After Effects Automation
- Maintain non-blocking HTTP / IPC communication with After Effects.
- Map layer references (`@LayerName`) to active composition layers.
- Provide instant feedback while waiting for AI generation.
