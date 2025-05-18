    import React, { useState, useEffect, useCallback, useRef, Component } from 'react';
    import io from 'socket.io-client';

    /**
     * Dashboard component - Trading application main interface
     *
     * Displays:
     * - Account balances and market status
     * - Available tickers to subscribe
     * - Active charts with error boundaries
     * - Real-time event log
     */
    class ChartErrorBoundary extends Component {
      constructor(props) {
        super(props);
        this.state = { hasError: false };
      }
      static getDerivedStateFromError() {
        return { hasError: true };
      }
      render() {
        if (this.state.hasError) {
          return (
            <div className="alert alert-danger p-3">
              <strong>Chart failed to load.</strong>
            </div>
          );
        }
        return this.props.children;
      }
    }

    function Dashboard({ account, loading, error }) {
      // separate state slices for clarity
      const [tickers, setTickers] = useState([]);
      const [positions, setPositions] = useState([]);
      const [activeCharts, setActiveCharts] = useState([]);
      const [events, setEvents] = useState([]);
      const [socket, setSocket] = useState(null);

      // dedupe exact duplicates
      const seenSignatures = useRef(new Set());
      // counters per namespace
      const counters = useRef({ ticker: 0, chart: 0, event: 0 });

      /** generate unique ID per namespace */
      const genId = useCallback((ns) => {
        counters.current[ns] = (counters.current[ns] || 0) + 1;
        return `${ns}-${counters.current[ns]}-${Math.random().toString(36).substr(2, 8)}`;
      }, []);

      /** add to event log, skipping duplicates */
      const addEvent = useCallback((type, raw) => {
        // stringify
        let msg;
        if (raw == null) msg = String(raw);
        else if (typeof raw === 'object') {
          try { msg = JSON.stringify(raw); }
          catch { msg = '[Object]'; }
        } else msg = String(raw);

        const sig = `${type}:${msg}`;
        if (seenSignatures.current.has(sig)) return;
        seenSignatures.current.add(sig);

        const id = genId('event');
        const evt = { id, timestamp: new Date().toISOString(), type, message: msg };
        setEvents(ev => [evt, ...ev].slice(0, 100));
      }, [genId]);

      // reset on mount
      useEffect(() => {
        setTickers([]);
        setPositions([]);
        setActiveCharts([]);
        setEvents([]);
        seenSignatures.current.clear();
        counters.current = { ticker: 0, chart: 0, event: 0 };
      }, []);

      // websocket
      useEffect(() => {
        const sock = io({ path: '/socket.io', reconnection: true, reconnectionDelay: 1000, reconnectionAttempts: 5 });
        sock.on('connect',    () => addEvent('system','WebSocket connected'));
        sock.on('disconnect', () => addEvent('system','WebSocket disconnected'));
        sock.on('error',      e   => addEvent('error',e));
        sock.on('market_update', d => {
          if (d?.symbol && d.price!=null) addEvent('market',`Update for ${d.symbol}: $${d.price}`);
          else addEvent('market','Invalid market_update');
        });
        sock.on('signal_update', d => {
          if (d?.symbol) addEvent('signal',`Signal ${d.symbol}: ${d.type||'unk'} ${d.price||''}`);
          else addEvent('signal','Invalid signal_update');
        });
        setSocket(sock);
        return ()=>sock.disconnect();
      }, [addEvent]);

      // fetch tickers
      useEffect(() => {
        fetch('/api/tickers')
          .then(r=>r.json())
          .then(arr=>{
            if (!Array.isArray(arr)) return addEvent('error','Bad tickers format');
            const uniq = Array.from(new Set(arr));
            setTickers(uniq.map(s=>({ id: genId('ticker'), symbol: s })));
          })
          .catch(()=>addEvent('error','Failed tickers fetch'));
      }, [addEvent, genId]);

      // fetch positions
      useEffect(() => {
        fetch('/api/positions')
          .then(r=>r.json())
          .then(arr=>{
            if (!Array.isArray(arr)) return addEvent('error','Bad positions format');
            setPositions(arr);
          })
          .catch(()=>addEvent('error','Failed positions fetch'));
      }, [addEvent]);

      // subscribe ticker
      const handleSubscribe = useCallback(sym=>{
        if (!socket) return;
        socket.emit('subscribe_ticker',{symbol:sym});
        addEvent('user',`Subscribed ${sym}`);
        setActiveCharts(chs=>chs.find(c=>c.symbol===sym)
          ? chs
          : [...chs,{ id: genId('chart'), symbol: sym }]
        );
      },[socket,addEvent,genId]);

      // loading/error
      if (loading) return <div className="text-center my-5"><div className="spinner-border"/><p>Loading…</p></div>;
      if (error) {
        const msg=typeof error==='string'?error:error.message||JSON.stringify(error);
        return <div className="alert alert-danger m-4"><h4>Error</h4><p>{msg}</p></div>;
      }

      return (
        <div className="container-fluid py-3">
          {/* Account cards omitted for brevity */}
          <div className="row">
            {/* sidebar */}
            <div className="col-md-3 mb-4">
              <div className="card h-100">
                <div className="card-header"><h5>Tickers</h5></div>
                <div className="list-group list-group-flush p-0">
                  {tickers.map(t=>(
                    <button
                      key={t.id}
                      className={`list-group-item list-group-item-action ${activeCharts.some(c=>c.symbol===t.symbol)?'active':''}`}
                      onClick={()=>handleSubscribe(t.symbol)}
                    >{t.symbol}</button>
                  ))}
                  {!tickers.length&&<div className="list-group-item text-center text-muted py-3">No tickers</div>}
                </div>
              </div>
            </div>
            {/* main */}
            <div className="col-md-9">
              <div className="row mb-4">
                {activeCharts.map(c=>(
                  <div key={c.id} className="col-md-6 mb-3">
                    <ChartErrorBoundary>
                      <div className="card">
                        <div className="card-header d-flex justify-content-between"><h5>{c.symbol}</h5>
                          <button className="btn btn-sm btn-outline-secondary" onClick={()=>setActiveCharts(chs=>chs.filter(x=>x.id!==c.id))}>&times;</button>
                        </div>
                        <div className="card-body"><div className="chart-container" id={`chart-${c.id}`}>Loading…</div></div>
                      </div>
                    </ChartErrorBoundary>
                  </div>
                ))}
                {!activeCharts.length&&<div className="col-12"><div className="alert alert-info">Select ticker</div></div>}
              </div>
              <div className="card">
                <div className="card-header"><h5>Events</h5></div>
                <div className="list-group list-group-flush" style={{maxHeight:250,overflowY:'auto'}}>
                  {events.map(e=>(
                    <div key={e.id} className="list-group-item py-2">
                      <small className="text-muted me-2">{new Date(e.timestamp).toLocaleTimeString()}</small>
                      <span className={`badge me-2 ${e.type==='error'?'bg-danger':e.type==='system'?'bg-secondary':e.type==='signal'?'bg-primary':'bg-success'}`}>{e.type}</span>
                      {e.message}
                    </div>
                  ))}
                  {!events.length&&<div className="list-group-item text-center text-muted py-3">No events</div>}
                </div>
              </div>
            </div>
          </div>
        </div>
      );
    }
    export default Dashboard;