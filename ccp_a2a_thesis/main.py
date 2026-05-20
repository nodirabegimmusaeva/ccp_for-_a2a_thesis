"""Main entry point for the CCP thesis experiment"""
import sys
import time
from experiments.runner import ExperimentRunner
from utils.visualizer import ResultsVisualizer
from config import NUM_TRIALS

def main():
    """Run the complete experiment"""
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║     CCP for A2A Protocols - Thesis Experiment           ║
    ║  Canonical Context Payloads for Reducing Context Drift  ║
    ╚══════════════════════════════════════════════════════════╝
    """)
    
    print(f"Configuration:")
    print(f"  - Number of trials: {NUM_TRIALS}")
    print(f"  - Task categories: Food, Flight, Workout, Laptop, Travel")
    print(f"  - Protocols: Text (unstructured) vs CCP (structured)")
    print()
    
    # Run experiment
    runner = ExperimentRunner()
    start_time = time.time()
    
    try:
        results = runner.run_full_experiment()
        elapsed = time.time() - start_time
        
        # Print final results
        print("\n" + "=" * 60)
        print("FINAL RESULTS")
        print("=" * 60)
        
        print(f"\n📊 Text Protocol:")
        print(f"   Mean Accuracy: {results['text']['mean_accuracy']:.1%} ± {results['text']['std_accuracy']:.1%}")
        print(f"   Mean CRS: {results['text']['mean_crs']:.3f} ± {results['text']['std_crs']:.3f}")
        
        print(f"\n📊 CCP Protocol:")
        print(f"   Mean Accuracy: {results['ccp']['mean_accuracy']:.1%} ± {results['ccp']['std_accuracy']:.1%}")
        print(f"   Mean CRS: {results['ccp']['mean_crs']:.3f} ± {results['ccp']['std_crs']:.3f}")
        
        improvement = results['ccp']['mean_accuracy'] - results['text']['mean_accuracy']
        print(f"\n📈 CCP Improvement: +{improvement:.1%} in accuracy")
        
        # Generate visualizations
        print("\n🎨 Generating visualizations...")
        visualizer = ResultsVisualizer()
        visualizer.plot_accuracy_comparison(results)
        visualizer.plot_crs_comparison(results)
        
        print(f"\n✅ Experiment completed in {elapsed:.1f} seconds")
        print(f"📁 Results saved to: results/, plots/, logs/")
        
        return results
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Experiment interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error during experiment: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()