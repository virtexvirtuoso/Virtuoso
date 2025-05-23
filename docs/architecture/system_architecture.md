# System Architecture

This document outlines the architectural design of our trading system.

## System Flow Diagram

```mermaid
flowchart TD
    %% External Data Sources
    Binance([Binance]):::exchange --> |Real-time|WS[WebSocket Handler]:::process
    Bybit([Bybit]):::exchange --> |Real-time|WS
    Coinbase([Coinbase]):::exchange --> |Real-time|WS
    Hyperliquid([Hyperliquid]):::exchange --> |Real-time|WS

    Binance --> |Historical|CCXT[CCXT Client]:::process
    Bybit --> |Historical|CCXT
    Coinbase --> |Historical|CCXT
    Hyperliquid --> |Historical|CCXT
    
    %% Data Acquisition Layer
    subgraph DataAcquisition["Data Acquisition"]
        WS & CCXT --> ErrH[Error Handler]:::caution
        ErrH --> DF[Data Fetcher]:::process
    end

    %% Data Processing & Storage
    subgraph DataCore["Data Core"]
        DF --> Validator{Validator}:::validation
        Validator --> Batcher[Batcher]:::process
        Batcher --> Storage[(Storage)]:::storage
    end

    %% Analysis Engine
    subgraph MarketPrism["Analysis Engine"]
        Storage --> AnalysisHub{Analysis Hub}:::process
        AnalysisHub --> |Technical|T[Technical]:::analysis
        AnalysisHub --> |Volume|V[Volume]:::analysis
        AnalysisHub --> |Orderflow|OF[Orderflow]:::analysis
        AnalysisHub --> |Orderbook|OB[Orderbook]:::analysis
        AnalysisHub --> |Price Structure|PS[Price Structure]:::analysis
        AnalysisHub --> |Sentiment|S[Sentiment]:::analysis
        
        T & V & OF & OB & PS & S --> INT[Interpretations]:::interpretation
    end

    %% Signal Generation & Execution
    subgraph Trading["Trading System"]
        INT --> CA[Confluence Analyzer]:::analysis
        CA --> SW[Score Weighting]:::analysis
        SW --> MLV[ML Validation]:::analytical-machine
        MLV --> SG[Signal Generator]:::signal
        SG --> PS2[Position Sizing]:::execution
        PS2 --> RM{Risk Management}:::execution
        RM --> OM[Order Manager]:::execution
    end

    %% API
    SG --> REST[REST API]:::api

    %% Simplified class definitions
    classDef exchange fill:#bbf,stroke:#333,stroke-width:1px;
    classDef process fill:#f9f,stroke:#333,stroke-width:1px;
    classDef caution fill:#f96,stroke:#333,stroke-width:1px;
    classDef validation fill:#9f9,stroke:#333,stroke-width:1px;
    classDef storage fill:#f96,stroke:#333,stroke-width:1px;
    classDef analysis fill:#ff9,stroke:#333,stroke-width:1px;
    classDef interpretation fill:#f66,stroke:#333,stroke-width:1px;
    classDef execution fill:#6ff,stroke:#333,stroke-width:1px;
    classDef api fill:#9f9,stroke:#333,stroke-width:1px;
    classDef analytical-machine fill:#c9f,stroke:#333,stroke-width:1px;
    classDef signal fill:#fc9,stroke:#333,stroke-width:1px;
```

## Component Descriptions

### Data Sources
- **Exchanges**: Binance, Bybit, Coinbase, and Hyperliquid provide both real-time and historical market data

### Data Acquisition
- **WebSocket Handler**: Processes real-time data streams from exchanges
- **CCXT Client**: Fetches historical data and provides standardized access to exchange APIs
- **Error Handler**: Manages error detection, logging, and recovery strategies
- **Data Fetcher**: Standardizes data formats from different sources

### Data Core
- **Validator**: Ensures data integrity and quality
- **Batcher**: Aggregates and organizes data for efficient storage
- **Storage**: Unified storage interface for both cache (Redis) and permanent storage (PostgreSQL)

### Analysis Engine
- **Analysis Hub**: Central coordinator for all analysis modules
- **Analysis Modules**: Specialized components for different analysis types
- **Interpretations**: Consolidates findings from all analysis modules

### Trading System
- **Confluence Analyzer**: Identifies agreement across multiple analysis dimensions
- **Score Weighting**: Applies appropriate importance to different signals
- **ML Validation**: Uses machine learning to validate signal quality
- **Signal Generator**: Creates actionable trading signals
- **Position Sizing**: Determines appropriate position size based on risk parameters
- **Risk Management**: Applies risk constraints and checks
- **Order Manager**: Handles the execution logistics of trades

### API
- **REST API**: Provides external access to signals and system data 