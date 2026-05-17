
## [0.1.0] - 2026-05-16

### Added

- Initial implementation of Qwen2.5-1.5B-Instruct based extraction pipeline
- Structured incident schema:
  - incident summary
  - event timeline
  - entity extraction (devices, circuits, technicians)
  - conflict detection field
  - final resolution field
- MLflow experiment tracking integration
- Prompt versioning support (PROMPT_V1)
- JSON schema validation checks
- Latency measurement for inference benchmarking

---

### Experimental Result (Baseline Run)

The system successfully extracted structured incident data from noisy dispatch logs.


#### input Example

```text
INC-99102

System monitoring detected intermittent packet loss on core switch cluster in Toronto data node TD-14.

Initial alert triggered at 03:41 AM when ICMP ping failures exceeded threshold (packet loss > 40%) for IP range 10.22.14.0/24.

NOC engineer report:
Multiple devices intermittently responding. Device SW-CORE-19 shows unstable connectivity. SSH access failed twice.

At 03:58 AM, logs show repeated ICMP timeout for 10.22.14.23 and 10.22.14.31.

A technician was dispatched but initial remote diagnostics were inconclusive due to network flapping.

On-site technician report (Alex P.):
Device SW-CORE-19 completely unresponsive to ping and console access.
Physical inspection revealed NIC card failure suspected after overheating warning logs.

Replacement procedure initiated:
- removed faulty network interface card
- installed replacement NIC module
- rebooted device

By 05:10 AM, device restored and stable ping response confirmed.

Customer impact: intermittent service degradation across VLAN 220-245.

Next action: monitor stability for 24 hours and confirm no packet loss recurrence.


```
#### Expecetd Output Example
Elapsed time: 162.50 seconds

```json
{
  "incident_summary": "Packet loss and intermittent failure on SW-CORE-19 due to suspected NIC hardware failure in Toronto node TD-14.",
  "event_timeline": [
    {
      "timestamp": "03:41 AM",
      "event": "ICMP packet loss > 40% detected for 10.22.14.0/24",
      "source": "System Monitoring"
    },
    {
      "timestamp": "03:58 AM",
      "event": "Repeated ICMP timeouts for 10.22.14.23 and 10.22.14.31",
      "source": "Logs"
    },
    {
      "timestamp": "04:05 AM",
      "event": "SSH and console access failures observed on SW-CORE-19",
      "source": "NOC Engineer"
    },
    {
      "timestamp": "04:20 AM",
      "event": "On-site inspection initiated after remote diagnostics failed",
      "source": "Technician Report"
    },
    {
      "timestamp": "05:10 AM",
      "event": "NIC replacement completed and device rebooted",
      "source": "Technician Report"
    }
  ],
  "entities": {
    "devices": ["SW-CORE-19"],
    "circuits": [],
    "technicians": ["Alex P."],
    "ips": ["10.22.14.0/24", "10.22.14.23", "10.22.14.31"]
  },
  "conflicts_detected": [
    "Intermittent vs sustained failure ambiguity in network reports",
    "Remote diagnostics inconclusive while hardware failure suspected"
  ],
  "final_resolution": "NIC replacement and reboot restored stable connectivity; monitoring initiated for 24 hours."
}
```
