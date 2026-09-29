import 'package:flutter/material.dart';
import 'screens/dashboard.dart';

void main() => runApp(const FxBotApp());

class FxBotApp extends StatelessWidget {
  const FxBotApp({super.key});

  @override
  Widget build(BuildContext context) {
    final base = ThemeData.dark(useMaterial3: true);
    return MaterialApp(
      title: 'FX Bot',
      debugShowCheckedModeBanner: false,
      theme: base.copyWith(
        colorScheme: const ColorScheme.dark(
          primary: Color(0xFF4CC38A),
          secondary: Color(0xFFE05C5C),
          surface: Color(0xFF141821),
        ),
        scaffoldBackgroundColor: const Color(0xFF0B0E14),
        cardTheme: CardThemeData(
          color: const Color(0xFF141821),
          elevation: 0,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
        ),
        textTheme: base.textTheme.apply(fontFamily: 'monospace'),
      ),
      home: const DashboardScreen(),
    );
  }
}
