"""
Task 4: Post-Processing Quality Check
Parsing Audit Script

Validates parser performance across A+ message variations and provides comprehensive audit report.
"""
import json
import sys
from datetime import datetime
from typing import Dict, Any, List, Tuple

sys.path.append('.')
from app import create_app


def run_parsing_audit() -> Dict[str, Any]:
    """
    Run comprehensive parsing audit for A+ messages.
    
    Returns:
        Dictionary with audit results including success rate and examples
    """
    app = create_app()
    
    with app.app_context():
        from app import db
        from sqlalchemy import text
        
        session = db.session
        
        # Query all A+ messages
        aplus_query = text("""
            SELECT id, content, is_processed, timestamp, channel_id
            FROM discord_messages 
            WHERE content ILIKE '%A+%Setup%' 
            ORDER BY timestamp DESC
        """)
        
        aplus_messages = session.execute(aplus_query).fetchall()
        total_aplus = len(aplus_messages)
        
        if total_aplus == 0:
            return {
                "total": 0,
                "parsed": 0,
                "unparsed": 0,
                "success_rate": "0%",
                "message": "No A+ messages found in database"
            }
        
        # Count parsed vs unparsed
        parsed_messages = [msg for msg in aplus_messages if msg.is_processed]
        unparsed_messages = [msg for msg in aplus_messages if not msg.is_processed]
        
        parsed_count = len(parsed_messages)
        unparsed_count = len(unparsed_messages)
        success_rate = round((parsed_count / total_aplus) * 100, 1)
        
        # Get examples of successful messages with setup counts
        successful_examples = []
        if parsed_messages:
            for msg in parsed_messages[:3]:  # Top 3 successful examples
                setup_query = text("""
                    SELECT COUNT(*) as setup_count, 
                           COUNT(DISTINCT ticker) as ticker_count,
                           STRING_AGG(DISTINCT label, ', ') as labels
                    FROM trade_setups 
                    WHERE message_id = :message_id
                """)
                
                setup_result = session.execute(setup_query, {"message_id": str(msg.id)}).fetchone()
                
                successful_examples.append({
                    "message_id": msg.id,
                    "timestamp": msg.timestamp.isoformat(),
                    "setups_created": setup_result.setup_count if setup_result else 0,
                    "tickers_parsed": setup_result.ticker_count if setup_result else 0,
                    "labels_found": setup_result.labels if setup_result else "",
                    "content_preview": msg.content[:150] + "..." if len(msg.content) > 150 else msg.content
                })
        
        # Get examples of failed messages with failure reasons
        failed_examples = []
        if unparsed_messages:
            for msg in unparsed_messages[:3]:  # Top 3 failed examples
                # Try to get failure reason from parsing_failures table if it exists
                try:
                    failure_query = text("""
                        SELECT reason, details, created_at
                        FROM parsing_failures 
                        WHERE message_id = :message_id 
                        ORDER BY created_at DESC 
                        LIMIT 1
                    """)
                    
                    failure_result = session.execute(failure_query, {"message_id": str(msg.id)}).fetchone()
                    failure_reason = failure_result.reason if failure_result else "unknown"
                    failure_details = failure_result.details if failure_result else "No failure details available"
                except:
                    failure_reason = "unknown"
                    failure_details = "Failure tracking table not available"
                
                failed_examples.append({
                    "message_id": msg.id,
                    "timestamp": msg.timestamp.isoformat(),
                    "failure_reason": failure_reason,
                    "failure_details": failure_details,
                    "content_preview": msg.content[:150] + "..." if len(msg.content) > 150 else msg.content
                })
        
        # Analysis of parsing patterns
        pattern_analysis = analyze_message_patterns(list(aplus_messages), session)
        
        session.close()
        
        return {
            "total": total_aplus,
            "parsed": parsed_count,
            "unparsed": unparsed_count,
            "success_rate": f"{success_rate}%",
            "audit_timestamp": datetime.utcnow().isoformat(),
            "successful_examples": successful_examples,
            "failed_examples": failed_examples,
            "pattern_analysis": pattern_analysis
        }


def analyze_message_patterns(messages: List, session) -> Dict[str, Any]:
    """
    Analyze patterns in A+ messages to understand parsing success factors.
    
    Args:
        messages: List of A+ messages
        session: Database session
        
    Returns:
        Dictionary with pattern analysis
    """
    patterns = {
        "header_variations": {},
        "ticker_formats": {},
        "content_length_analysis": {
            "successful": [],
            "failed": []
        }
    }
    
    for msg in messages:
        content = msg.content
        content_length = len(content)
        
        # Analyze header variations
        lines = content.split('\n')
        if lines:
            header = lines[0].strip()
            if header not in patterns["header_variations"]:
                patterns["header_variations"][header] = {"count": 0, "parsed": 0}
            patterns["header_variations"][header]["count"] += 1
            if msg.is_processed:
                patterns["header_variations"][header]["parsed"] += 1
        
        # Analyze ticker formats (look for common patterns)
        if "✅" in content:
            ticker_format = "checkmark"
        elif any(f"**{ticker}**" in content for ticker in ["SPY", "TSLA", "AAPL", "NVDA", "GOOGL"]):
            ticker_format = "bold"
        else:
            ticker_format = "plain"
            
        if ticker_format not in patterns["ticker_formats"]:
            patterns["ticker_formats"][ticker_format] = {"count": 0, "parsed": 0}
        patterns["ticker_formats"][ticker_format]["count"] += 1
        if msg.is_processed:
            patterns["ticker_formats"][ticker_format]["parsed"] += 1
        
        # Content length analysis
        if msg.is_processed:
            patterns["content_length_analysis"]["successful"].append(content_length)
        else:
            patterns["content_length_analysis"]["failed"].append(content_length)
    
    # Calculate averages
    if patterns["content_length_analysis"]["successful"]:
        patterns["avg_successful_length"] = sum(patterns["content_length_analysis"]["successful"]) / len(patterns["content_length_analysis"]["successful"])
    else:
        patterns["avg_successful_length"] = 0
        
    if patterns["content_length_analysis"]["failed"]:
        patterns["avg_failed_length"] = sum(patterns["content_length_analysis"]["failed"]) / len(patterns["content_length_analysis"]["failed"])
    else:
        patterns["avg_failed_length"] = 0
    
    # Remove raw length arrays for cleaner output
    del patterns["content_length_analysis"]
    
    return patterns


def main():
    """Main function to run parsing audit and display results."""
    print("🔍 Running Task 4: Post-Processing Quality Check")
    print("=" * 60)
    
    try:
        audit_results = run_parsing_audit()
        
        # Display core metrics
        print("\n📊 PARSING AUDIT RESULTS")
        print("-" * 30)
        
        core_report = {
            "total": audit_results["total"],
            "parsed": audit_results["parsed"], 
            "unparsed": audit_results["unparsed"],
            "success_rate": audit_results["success_rate"]
        }
        
        print(json.dumps(core_report, indent=2))
        
        # Display detailed analysis
        print(f"\n✅ SUCCESSFUL PARSING EXAMPLES ({len(audit_results.get('successful_examples', []))} shown)")
        print("-" * 50)
        
        for i, example in enumerate(audit_results.get('successful_examples', []), 1):
            print(f"\n[{i}] Message ID: {example['message_id']}")
            print(f"    Timestamp: {example['timestamp']}")
            print(f"    Setups Created: {example['setups_created']}")
            print(f"    Tickers Parsed: {example['tickers_parsed']}")
            print(f"    Labels Found: {example['labels_found']}")
            print(f"    Content: {example['content_preview']}")
        
        print(f"\n❌ FAILED PARSING EXAMPLES ({len(audit_results.get('failed_examples', []))} shown)")
        print("-" * 50)
        
        for i, example in enumerate(audit_results.get('failed_examples', []), 1):
            print(f"\n[{i}] Message ID: {example['message_id']}")
            print(f"    Timestamp: {example['timestamp']}")
            print(f"    Failure Reason: {example['failure_reason']}")
            print(f"    Failure Details: {example['failure_details']}")
            print(f"    Content: {example['content_preview']}")
        
        # Display pattern analysis
        if 'pattern_analysis' in audit_results:
            print(f"\n📈 PATTERN ANALYSIS")
            print("-" * 30)
            
            patterns = audit_results['pattern_analysis']
            
            print(f"\nHeader Variations:")
            for header, stats in patterns.get('header_variations', {}).items():
                success_rate = round((stats['parsed'] / stats['count']) * 100, 1) if stats['count'] > 0 else 0
                print(f"  '{header}': {stats['parsed']}/{stats['count']} ({success_rate}%)")
            
            print(f"\nTicker Formats:")
            for format_type, stats in patterns.get('ticker_formats', {}).items():
                success_rate = round((stats['parsed'] / stats['count']) * 100, 1) if stats['count'] > 0 else 0
                print(f"  {format_type}: {stats['parsed']}/{stats['count']} ({success_rate}%)")
            
            print(f"\nContent Length Analysis:")
            print(f"  Average successful message length: {patterns.get('avg_successful_length', 0):.0f} chars")
            print(f"  Average failed message length: {patterns.get('avg_failed_length', 0):.0f} chars")
        
        # Log complete results as JSON
        print(f"\n💾 COMPLETE AUDIT LOG")
        print("-" * 30)
        print(json.dumps(audit_results, indent=2))
        
        print(f"\n✅ Task 4 Quality Check Complete")
        print(f"Audit completed at: {audit_results.get('audit_timestamp', 'unknown')}")
        
    except Exception as e:
        print(f"❌ Error running parsing audit: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()