import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../models.dart';

class CalendarList extends StatelessWidget {
  final List<CalendarEvent> events;
  const CalendarList({super.key, required this.events});

  @override
  Widget build(BuildContext context) {
    if (events.isEmpty) return const Center(child: Text('No events'));
    final fmt = DateFormat('EEE MMM d, HH:mm');
    return ListView.separated(
      padding: const EdgeInsets.all(16),
      itemCount: events.length,
      separatorBuilder: (_, __) => const SizedBox(height: 6),
      itemBuilder: (_, i) {
        final e = events[i];
        final impactColor = switch (e.impact) {
          'high' => const Color(0xFFE05C5C),
          'medium' => const Color(0xFFE0A85C),
          _ => Colors.grey,
        };
        return Card(
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: Row(
              children: [
                Container(
                  width: 8, height: 40,
                  decoration: BoxDecoration(
                    color: impactColor,
                    borderRadius: BorderRadius.circular(4),
                  ),
                ),
                const SizedBox(width: 12),
                SizedBox(
                  width: 46,
                  child: Text(e.currency,
                      style: Theme.of(context).textTheme.titleMedium),
                ),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(e.title, maxLines: 1, overflow: TextOverflow.ellipsis),
                      Text(fmt.format(e.time.toLocal()),
                          style: Theme.of(context).textTheme.bodySmall),
                    ],
                  ),
                ),
                _Cell(label: 'Act', value: e.actual),
                _Cell(label: 'Fcst', value: e.forecast),
                _Cell(label: 'Prev', value: e.previous),
              ],
            ),
          ),
        );
      },
    );
  }
}

class _Cell extends StatelessWidget {
  final String label;
  final String? value;
  const _Cell({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 58,
      child: Column(
        children: [
          Text(label, style: const TextStyle(fontSize: 10, color: Colors.grey)),
          Text(value ?? '—', style: Theme.of(context).textTheme.bodyMedium),
        ],
      ),
    );
  }
}
