# A+ Trading App

A sophisticated options trading application that automates the process of parsing trading signals, selecting appropriate options contracts, and executing paper trades through Alpaca API.

## Overview

The A+ Trading App is designed for traders who receive setup messages from various sources (like Discord or email) and want to automatically execute options trades based on those signals. The application features:

- Ingestion of setup messages through webhooks
- Advanced parsing of trading signals, targets, and biases
- Real-time market monitoring via Alpaca WebSocket
- Options chain fetching and Greek calculations
- Automated trade execution on signal triggers
- Position management and exit rules
- Web-based dashboard for monitoring activity

![A+ Trading App Architecture](https://i.ibb.co/jD3Q5Bt/architecture.png)

## Getting Started

### Prerequisites

- Python 3.8+
- Redis server
- Alpaca Paper Trading account

### Environment Variables

The following environment variables should be set:

