import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:url_launcher/url_launcher.dart';
import '../models.dart';

class NewsList extends StatelessWidget {
  final List<NewsItem> news;
  const NewsList({super.key, required this.news});

  @override
  Widget build(BuildContext context) {
    if (news.isEmpty) return const Center(child: Text('No news yet'));
    final fmt = DateFormat('MMM d, HH:mm');
    return ListView.separated(
      padding: const EdgeInsets.all(16),
      itemCount: news.length,
      separatorBuilder: (_, __) => const SizedBox(height: 8),
      itemBuilder: (_, i) {
        final n = news[i];
        return Card(
          child: InkWell(
            borderRadius: BorderRadius.circular(10),
            onTap: () => launchUrl(Uri.parse(n.url)),
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      _SentimentBadge(sentiment: n.sentiment),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          '${n.source} · ${fmt.format(n.published.toLocal())}',
                          style: Theme.of(context).textTheme.bodySmall,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                      if (n.pairs.isNotEmpty)
                        Wrap(
                          spacing: 4,
                          children: n.pairs
                              .take(3)
                              .map((p) => Chip(
                                    label: Text(p, style: const TextStyle(fontSize: 10)),
                                    visualDensity: VisualDensity.compact,
                                    padding: EdgeInsets.zero,
                                    materialTapTargetSize:
                                        MaterialTapTargetSize.shrinkWrap,
                                  ))
                              .toList(),
                        ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  Text(n.title,
                      style: Theme.of(context).textTheme.titleMedium,
                      maxLines: 2, overflow: TextOverflow.ellipsis),
                  if (n.summary.isNotEmpty) ...[
                    const SizedBox(height: 4),
                    Text(n.summary,
                        style: Theme.of(context).textTheme.bodySmall,
                        maxLines: 3, overflow: TextOverflow.ellipsis),
                  ],
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}

class _SentimentBadge extends StatelessWidget {
  final String? sentiment;
  const _SentimentBadge({required this.sentiment});

  @override
  Widget build(BuildContext context) {
    Color c;
    IconData ic;
    switch (sentiment) {
      case 'bullish':
        c = const Color(0xFF4CC38A);
        ic = Icons.trending_up;
        break;
      case 'bearish':
        c = const Color(0xFFE05C5C);
        ic = Icons.trending_down;
        break;
      default:
        c = Colors.grey;
        ic = Icons.trending_flat;
    }
    return Icon(ic, color: c, size: 18);
  }
}
