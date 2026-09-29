class NewsItem {
  final String id;
  final String title;
  final String summary;
  final String url;
  final String source;
  final DateTime published;
  final String? sentiment;
  final double? sentimentScore;
  final List<String> pairs;

  NewsItem({
    required this.id,
    required this.title,
    required this.summary,
    required this.url,
    required this.source,
    required this.published,
    this.sentiment,
    this.sentimentScore,
    this.pairs = const [],
  });

  factory NewsItem.fromJson(Map<String, dynamic> j) => NewsItem(
        id: j['id'],
        title: j['title'] ?? '',
        summary: j['summary'] ?? '',
        url: j['url'] ?? '',
        source: j['source'] ?? '',
        published: DateTime.parse(j['published']),
        sentiment: j['sentiment'],
        sentimentScore: (j['sentiment_score'] as num?)?.toDouble(),
        pairs: List<String>.from(j['pairs'] ?? []),
      );
}

class PriceTick {
  final String pair;
  final double price;
  final double changePct;
  final DateTime timestamp;

  PriceTick({
    required this.pair,
    required this.price,
    required this.changePct,
    required this.timestamp,
  });

  factory PriceTick.fromJson(Map<String, dynamic> j) => PriceTick(
        pair: j['pair'],
        price: (j['price'] as num).toDouble(),
        changePct: (j['change_pct'] as num).toDouble(),
        timestamp: DateTime.parse(j['timestamp']),
      );
}

class Signal {
  final String pair;
  final String direction;
  final double strength;
  final String strategy;
  final String reason;
  final DateTime generatedAt;

  Signal({
    required this.pair,
    required this.direction,
    required this.strength,
    required this.strategy,
    required this.reason,
    required this.generatedAt,
  });

  factory Signal.fromJson(Map<String, dynamic> j) => Signal(
        pair: j['pair'],
        direction: j['direction'],
        strength: (j['strength'] as num).toDouble(),
        strategy: j['strategy'],
        reason: j['reason'],
        generatedAt: DateTime.parse(j['generated_at']),
      );
}

class CalendarEvent {
  final String id;
  final DateTime time;
  final String currency;
  final String title;
  final String impact;
  final String? actual;
  final String? forecast;
  final String? previous;

  CalendarEvent({
    required this.id,
    required this.time,
    required this.currency,
    required this.title,
    required this.impact,
    this.actual,
    this.forecast,
    this.previous,
  });

  factory CalendarEvent.fromJson(Map<String, dynamic> j) => CalendarEvent(
        id: j['id'],
        time: DateTime.parse(j['time']),
        currency: j['currency'] ?? '',
        title: j['title'] ?? '',
        impact: j['impact'] ?? 'low',
        actual: j['actual'],
        forecast: j['forecast'],
        previous: j['previous'],
      );
}

class DashboardSnapshot {
  final List<PriceTick> prices;
  final List<NewsItem> news;
  final List<Signal> signals;
  final List<CalendarEvent> calendar;
  final DateTime generatedAt;

  DashboardSnapshot({
    required this.prices,
    required this.news,
    required this.signals,
    required this.calendar,
    required this.generatedAt,
  });

  factory DashboardSnapshot.fromJson(Map<String, dynamic> j) => DashboardSnapshot(
        prices: (j['prices'] as List).map((e) => PriceTick.fromJson(e)).toList(),
        news: (j['news'] as List).map((e) => NewsItem.fromJson(e)).toList(),
        signals: (j['signals'] as List).map((e) => Signal.fromJson(e)).toList(),
        calendar: (j['calendar'] as List).map((e) => CalendarEvent.fromJson(e)).toList(),
        generatedAt: DateTime.parse(j['generated_at']),
      );
}
