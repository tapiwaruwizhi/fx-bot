import 'package:flutter/material.dart';
import '../models.dart';

class SignalsList extends StatelessWidget {
  final List<Signal> signals;
  const SignalsList({super.key, required this.signals});

  @override
  Widget build(BuildContext context) {
    if (signals.isEmpty) return const Center(child: Text('No signals yet'));
    return ListView.separated(
      padding: const EdgeInsets.all(16),
      itemCount: signals.length,
      separatorBuilder: (_, __) => const SizedBox(height: 8),
      itemBuilder: (_, i) {
        final s = signals[i];
        final color = switch (s.direction) {
          'BUY' => const Color(0xFF4CC38A),
          'SELL' => const Color(0xFFE05C5C),
          _ => Colors.grey,
        };
        return Card(
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Row(
              children: [
                Container(
                  width: 60,
                  padding: const EdgeInsets.symmetric(vertical: 6),
                  decoration: BoxDecoration(
                    color: color.withOpacity(0.15),
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(color: color),
                  ),
                  child: Text(
                    s.direction,
                    textAlign: TextAlign.center,
                    style: TextStyle(color: color, fontWeight: FontWeight.bold),
                  ),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Text(s.pair,
                              style: Theme.of(context).textTheme.titleMedium),
                          const SizedBox(width: 8),
                          Text('· ${s.strategy}',
                              style: Theme.of(context).textTheme.bodySmall),
                        ],
                      ),
                      const SizedBox(height: 4),
                      Text(s.reason,
                          style: Theme.of(context).textTheme.bodyMedium),
                    ],
                  ),
                ),
                const SizedBox(width: 12),
                SizedBox(
                  width: 60,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      Text('${(s.strength * 100).toStringAsFixed(0)}%',
                          style: Theme.of(context).textTheme.titleMedium),
                      const Text('strength', style: TextStyle(fontSize: 10)),
                    ],
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}
