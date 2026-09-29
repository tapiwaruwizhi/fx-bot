import 'dart:async';
import 'package:flutter/material.dart';
import '../api.dart';
import '../models.dart';
import '../widgets/price_grid.dart';
import '../widgets/news_list.dart';
import '../widgets/signals_list.dart';
import '../widgets/calendar_list.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  final api = ApiService();
  DashboardSnapshot? snapshot;
  String? error;
  StreamSubscription? _sub;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final snap = await api.fetchSnapshot();
      setState(() {
        snapshot = snap;
        error = null;
      });
      _sub = api.connect().listen(_onMessage, onError: (e) {
        setState(() => error = 'WebSocket: $e');
      });
    } catch (e) {
      setState(() => error = '$e');
    }
  }

  void _onMessage(Map<String, dynamic> msg) {
    if (snapshot == null) return;
    final type = msg['type'];
    final data = msg['data'];
    setState(() {
      switch (type) {
        case 'snapshot':
          snapshot = DashboardSnapshot.fromJson(data);
          break;
        case 'news':
          snapshot = DashboardSnapshot(
            prices: snapshot!.prices,
            news: (data as List).map((e) => NewsItem.fromJson(e)).toList(),
            signals: snapshot!.signals,
            calendar: snapshot!.calendar,
            generatedAt: DateTime.now(),
          );
          break;
        case 'prices':
          snapshot = DashboardSnapshot(
            prices: (data as List).map((e) => PriceTick.fromJson(e)).toList(),
            news: snapshot!.news,
            signals: snapshot!.signals,
            calendar: snapshot!.calendar,
            generatedAt: DateTime.now(),
          );
          break;
        case 'signals':
          snapshot = DashboardSnapshot(
            prices: snapshot!.prices,
            news: snapshot!.news,
            signals: (data as List).map((e) => Signal.fromJson(e)).toList(),
            calendar: snapshot!.calendar,
            generatedAt: DateTime.now(),
          );
          break;
        case 'calendar':
          snapshot = DashboardSnapshot(
            prices: snapshot!.prices,
            news: snapshot!.news,
            signals: snapshot!.signals,
            calendar: (data as List).map((e) => CalendarEvent.fromJson(e)).toList(),
            generatedAt: DateTime.now(),
          );
          break;
      }
    });
  }

  @override
  void dispose() {
    _sub?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (error != null && snapshot == null) {
      return Scaffold(
        body: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.error_outline, size: 48),
              const SizedBox(height: 12),
              Text(error!),
              const SizedBox(height: 12),
              FilledButton(onPressed: _load, child: const Text('Retry')),
            ],
          ),
        ),
      );
    }
    if (snapshot == null) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }

    return DefaultTabController(
      length: 4,
      child: Scaffold(
        appBar: AppBar(
          title: Row(
            children: [
              const Text('FX Bot'),
              const SizedBox(width: 12),
              Text(
                '· updated ${_fmtTime(snapshot!.generatedAt)}',
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ],
          ),
          bottom: const TabBar(
            tabs: [
              Tab(icon: Icon(Icons.show_chart), text: 'Prices'),
              Tab(icon: Icon(Icons.article_outlined), text: 'News'),
              Tab(icon: Icon(Icons.bolt_outlined), text: 'Signals'),
              Tab(icon: Icon(Icons.event_note_outlined), text: 'Calendar'),
            ],
          ),
        ),
        body: TabBarView(
          children: [
            PriceGrid(prices: snapshot!.prices),
            NewsList(news: snapshot!.news),
            SignalsList(signals: snapshot!.signals),
            CalendarList(events: snapshot!.calendar),
          ],
        ),
      ),
    );
  }

  String _fmtTime(DateTime dt) {
    final l = dt.toLocal();
    two(int n) => n.toString().padLeft(2, '0');
    return '${two(l.hour)}:${two(l.minute)}:${two(l.second)}';
  }
}
